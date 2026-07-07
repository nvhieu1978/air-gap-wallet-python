import os
import subprocess
import json
import re

class TransactionBuilder:
    def __init__(self, config):
        self.config = config

    def _get_cli_path(self):
        return self.config.get("cardano_cli_path") or "cardano-cli"

    def _get_network_args(self):
        return self.config.network_param

    def _parse_fee(self, fee_raw):
        """Parse fee value from cardano-cli output (handles JSON and plain text)."""
        fee = None
        if "fee" in fee_raw:
            try:
                data = json.loads(fee_raw)
                fee = data.get("fee")
            except:
                pass
        if fee is None:
            # Fallback to regex matching first number
            match = re.search(r'\b\d+\b', fee_raw)
            if match:
                fee = int(match.group(0))
        return fee

    def build_standard_tx(self, sender_address, destination_address, amount_lovelace, selected_utxos, pparams_path, latest_slot, output_raw_path, temp_dir, dust_action="raise"):
        """
        Build a standard ADA transfer transaction raw body.
        Returns: (cbor_hex, fee, change)
        """
        cli_path = self._get_cli_path()
        network_args = self._get_network_args()
        
        ttl = latest_slot + 10000
        
        # Prepare inputs
        tx_in_args = []
        input_lovelace = 0
        for utxo in selected_utxos:
            tx_in_args.extend(["--tx-in", f"{utxo['tx_hash']}#{utxo['tx_index']}"])
            # Find lovelace amount in UTXO
            for amount in utxo["amount"]:
                if amount["unit"] == "lovelace":
                    input_lovelace += int(amount["quantity"])
                    break

        if input_lovelace < amount_lovelace:
            raise ValueError(f"Số dư khả dụng ({input_lovelace} Lovelace) nhỏ hơn lượng gửi đi ({amount_lovelace} Lovelace)")

        # 1. Build draft transaction
        draft_path = os.path.join(temp_dir, "tx.draft")
        build_draft_cmd = [
            cli_path, "conway", "transaction", "build-raw"
        ] + tx_in_args + [
            "--tx-out", f"{destination_address}+{amount_lovelace}",
            "--tx-out", f"{sender_address}+0",
            "--invalid-hereafter", str(ttl),
            "--fee", "0",
            "--protocol-params-file", pparams_path,
            "--out-file", draft_path
        ]
        
        subprocess.run(build_draft_cmd, check=True)

        # 2. Calculate min fee
        calc_fee_cmd = [
            cli_path, "conway", "transaction", "calculate-min-fee",
            "--tx-body-file", draft_path,
            "--witness-count", "1",
            "--protocol-params-file", pparams_path
        ] + network_args
        
        res = subprocess.run(calc_fee_cmd, capture_output=True, text=True, check=True)
        fee = self._parse_fee(res.stdout)
        if fee is None:
            raise RuntimeError(f"Không thể phân tích phí từ cardano-cli: {res.stdout}")

        # Add 2000 lovelace safety buffer
        fee += 2000
        
        # Calculate change
        change = input_lovelace - amount_lovelace - fee
        if change < 0:
            raise ValueError(f"Không đủ tiền để trang trải tiền gửi ({amount_lovelace} Lovelace) và phí ({fee} Lovelace).")

        # Handle dust limit (1 ADA = 1,000,000 Lovelace)
        min_utxo = 1000000
        if 0 < change < min_utxo:
            if dust_action == "donate":
                fee += change
                change = 0
            elif dust_action == "raise":
                return {
                    "status": "dust_warning",
                    "change": change,
                    "fee": fee,
                    "amount_lovelace": amount_lovelace,
                    "input_lovelace": input_lovelace
                }
            else:
                raise ValueError(f"Tiền thừa ({change} Lovelace) nhỏ hơn mức tối thiểu UTXO (1,000,000 Lovelace) và không thể trả về ví.")

        # 3. Build final raw transaction
        build_raw_cmd = [
            cli_path, "conway", "transaction", "build-raw"
        ] + tx_in_args + [
            "--tx-out", f"{destination_address}+{amount_lovelace}"
        ]
        
        if change > 0:
            build_raw_cmd.extend(["--tx-out", f"{sender_address}+{change}"])
            
        build_raw_cmd.extend([
            "--fee", str(fee),
            "--invalid-hereafter", str(ttl),
            "--out-file", output_raw_path
        ])
        
        subprocess.run(build_raw_cmd, check=True)

        with open(output_raw_path, "r") as f:
            raw_tx = json.load(f)

        cbor_hex = raw_tx.get("cborHex")
        if not cbor_hex:
            raise ValueError("File tx.raw không chứa dữ liệu cborHex.")

        return {
            "status": "success",
            "cbor_hex": cbor_hex,
            "fee": fee,
            "change": change
        }

    def build_delegation_tx(self, sender_address, stake_vkey_path, pool_id, drep_choice, drep_custom_id, is_registered, deposit, selected_utxos, pparams_path, latest_slot, output_raw_path, temp_dir, dust_action="raise"):
        """
        Build Conway governance registration & delegation transaction raw body.
        Returns: (cbor_hex, fee, change, deposit)
        """
        cli_path = self._get_cli_path()
        network_args = self._get_network_args()
        
        ttl = latest_slot + 1000
        
        # Prepare inputs
        tx_in_args = []
        input_lovelace = 0
        for utxo in selected_utxos:
            tx_in_args.extend(["--tx-in", f"{utxo['tx_hash']}#{utxo['tx_index']}"])
            for amount in utxo["amount"]:
                if amount["unit"] == "lovelace":
                    input_lovelace += int(amount["quantity"])
                    break

        # Generate DRep argument
        if drep_choice == "abstain":
            drep_arg = ["--always-abstain"]
        elif drep_choice == "no_confidence":
            drep_arg = ["--always-no-confidence"]
        elif drep_choice == "custom":
            drep_arg = ["--drep-key-hash", drep_custom_id]
        else:  # Default C2VN DRep
            default_drep = "drep1ygqlu72zwxszcx0kqdzst4k3g6fxx4klwcmpk0fcuujskvg3pmhgs"
            drep_arg = ["--drep-key-hash", default_drep]

        cert_path = os.path.join(temp_dir, "delegation.cert")

        # 1. Create delegation certificate
        if is_registered:
            cert_cmd = [
                cli_path, "conway", "stake-address", "stake-and-vote-delegation-certificate",
                "--stake-verification-key-file", stake_vkey_path,
                "--stake-pool-id", pool_id
            ] + drep_arg + [
                "--out-file", cert_path
            ]
        else:
            cert_cmd = [
                cli_path, "conway", "stake-address", "registration-stake-and-vote-delegation-certificate",
                "--stake-verification-key-file", stake_vkey_path,
                "--stake-pool-id", pool_id
            ] + drep_arg + [
                "--key-reg-deposit-amt", str(deposit),
                "--out-file", cert_path
            ]
            
        subprocess.run(cert_cmd, check=True)

        # 2. Build draft transaction
        draft_path = os.path.join(temp_dir, "tx.draft")
        build_draft_cmd = [
            cli_path, "conway", "transaction", "build-raw"
        ] + tx_in_args + [
            "--tx-out", f"{sender_address}+0",
            "--certificate-file", cert_path,
            "--invalid-hereafter", str(ttl),
            "--fee", "0",
            "--protocol-params-file", pparams_path,
            "--out-file", draft_path
        ]
        
        subprocess.run(build_draft_cmd, check=True)

        # 3. Calculate min fee (Requires 2 witness count since both payment and stake keys sign)
        calc_fee_cmd = [
            cli_path, "conway", "transaction", "calculate-min-fee",
            "--tx-body-file", draft_path,
            "--witness-count", "2",
            "--protocol-params-file", pparams_path
        ] + network_args
        
        res = subprocess.run(calc_fee_cmd, capture_output=True, text=True, check=True)
        fee = self._parse_fee(res.stdout)
        if fee is None:
            raise RuntimeError(f"Không thể phân tích phí từ cardano-cli: {res.stdout}")

        fee += 2000
        
        # Calculate change
        change = input_lovelace - deposit - fee
        if change < 0:
            raise ValueError(f"Không đủ tiền để thanh toán tiền cọc ({deposit} Lovelace) và phí ({fee} Lovelace).")

        # Handle dust limit
        min_utxo = 1000000
        if 0 < change < min_utxo:
            if dust_action == "donate":
                fee += change
                change = 0
            elif dust_action == "raise":
                return {
                    "status": "dust_warning",
                    "change": change,
                    "fee": fee,
                    "deposit": deposit,
                    "amount_lovelace": 0,
                    "input_lovelace": input_lovelace
                }
            else:
                raise ValueError(f"Tiền thừa ({change} Lovelace) nhỏ hơn mức tối thiểu UTXO (1,000,000 Lovelace) và không thể trả về ví.")

        # 4. Build final raw transaction
        build_raw_cmd = [
            cli_path, "conway", "transaction", "build-raw"
        ] + tx_in_args
        
        if change > 0:
            build_raw_cmd.extend(["--tx-out", f"{sender_address}+{change}"])
            
        build_raw_cmd.extend([
            "--certificate-file", cert_path,
            "--fee", str(fee),
            "--invalid-hereafter", str(ttl),
            "--out-file", output_raw_path
        ])
        
        subprocess.run(build_raw_cmd, check=True)

        with open(output_raw_path, "r") as f:
            raw_tx = json.load(f)

        cbor_hex = raw_tx.get("cborHex")
        if not cbor_hex:
            raise ValueError("File tx.raw không chứa dữ liệu cborHex.")

        return {
            "status": "success",
            "cbor_hex": cbor_hex,
            "fee": fee,
            "change": change,
            "deposit": deposit
        }
