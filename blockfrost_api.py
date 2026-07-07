import json
import os
import requests

class BlockfrostAPI:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    def check_config(self):
        """Check if API parameters are configured."""
        if not self.api_key:
            raise ValueError("BLOCKFROST_API_KEY chưa được cấu hình. Vui lòng vào Cài đặt.")
        if not self.base_url:
            raise ValueError("BLOCKFROST_URL chưa được cấu hình. Vui lòng vào Cài đặt.")

    def get_utxos(self, address):
        """Get UTXOs for a given address."""
        self.check_config()
        url = f"{self.base_url}/addresses/{address}/utxos"
        headers = {"project_id": self.api_key}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Lỗi khi kết nối Blockfrost: {e}")

    def get_latest_slot(self):
        """Get the latest slot number."""
        self.check_config()
        url = f"{self.base_url}/blocks/latest"
        headers = {"project_id": self.api_key}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            slot = data.get("slot")
            if slot is None:
                raise ValueError("Không tìm thấy trường slot trong thông tin block mới nhất.")
            return slot
        except requests.exceptions.RequestException as e:
            raise Exception(f"Lỗi khi lấy slot mới nhất: {e}")

    def check_stake_registered(self, stake_address):
        """Check if the stake address is registered on-chain."""
        self.check_config()
        url = f"{self.base_url}/accounts/{stake_address}"
        headers = {"project_id": self.api_key}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 404:
                return False
            response.raise_for_status()
            data = response.json()
            return data.get("active", False)
        except requests.exceptions.RequestException as e:
            # If the address is simply not on chain, Blockfrost returns 404/400.
            # Treat errors or inactive status as unregistered.
            return False

    def get_pparams(self, output_path="pparams.json", template_path="pparams_template.json"):
        """
        Fetch protocol parameters from Blockfrost and merge into cardano-cli format.
        """
        self.check_config()
        url = f"{self.base_url}/epochs/latest/parameters"
        headers = {"project_id": self.api_key}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            bf_params = response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Lỗi khi lấy tham số epoch từ Blockfrost: {e}")

        # Load template
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Không tìm thấy file mẫu tham số: {template_path}")
            
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)

        def safe_num(val, default_val=0):
            if val is None or val == "":
                return default_val
            try:
                if isinstance(val, (int, float)):
                    return val
                if "." in str(val):
                    return float(val)
                return int(val)
            except:
                return default_val

        # Merge Blockfrost parameters into template
        # Top-level variables
        template["txFeeFixed"] = safe_num(bf_params.get("min_fee_b"), template["txFeeFixed"])
        template["txFeePerByte"] = safe_num(bf_params.get("min_fee_a"), template["txFeePerByte"])
        
        utxo_cost = bf_params.get("coins_per_utxo_size") or bf_params.get("coins_per_utxo_word") or bf_params.get("min_utxo")
        template["utxoCostPerByte"] = safe_num(utxo_cost, template["utxoCostPerByte"])
        
        template["collateralPercentage"] = safe_num(bf_params.get("collateral_percent"), template["collateralPercentage"])
        template["maxBlockBodySize"] = safe_num(bf_params.get("max_block_size"), template["maxBlockBodySize"])
        template["maxBlockHeaderSize"] = safe_num(bf_params.get("max_block_header_size"), template["maxBlockHeaderSize"])
        template["maxTxSize"] = safe_num(bf_params.get("max_tx_size"), template["maxTxSize"])
        template["maxValueSize"] = safe_num(bf_params.get("max_val_size"), template["maxValueSize"])
        template["stakeAddressDeposit"] = safe_num(bf_params.get("key_deposit"), template["stakeAddressDeposit"])
        template["stakePoolDeposit"] = safe_num(bf_params.get("pool_deposit"), template["stakePoolDeposit"])
        template["minPoolCost"] = safe_num(bf_params.get("min_pool_cost"), template["minPoolCost"])
        template["poolRetireMaxEpoch"] = safe_num(bf_params.get("e_max"), template["poolRetireMaxEpoch"])
        
        # Nested structures
        if "executionUnitPrices" in template:
            template["executionUnitPrices"]["priceMemory"] = safe_num(
                bf_params.get("price_mem"), template["executionUnitPrices"]["priceMemory"]
            )
            template["executionUnitPrices"]["priceSteps"] = safe_num(
                bf_params.get("price_step"), template["executionUnitPrices"]["priceSteps"]
            )
            
        if "protocolVersion" in template:
            template["protocolVersion"]["major"] = safe_num(
                bf_params.get("protocol_major"), template["protocolVersion"]["major"]
            )
            template["protocolVersion"]["minor"] = safe_num(
                bf_params.get("protocol_minor"), template["protocolVersion"]["minor"]
            )
            
        if "maxBlockExecutionUnits" in template:
            template["maxBlockExecutionUnits"]["memory"] = safe_num(
                bf_params.get("max_block_ex_mem"), template["maxBlockExecutionUnits"]["memory"]
            )
            template["maxBlockExecutionUnits"]["steps"] = safe_num(
                bf_params.get("max_block_ex_steps"), template["maxBlockExecutionUnits"]["steps"]
            )
            
        if "maxTxExecutionUnits" in template:
            template["maxTxExecutionUnits"]["memory"] = safe_num(
                bf_params.get("max_tx_ex_mem"), template["maxTxExecutionUnits"]["memory"]
            )
            template["maxTxExecutionUnits"]["steps"] = safe_num(
                bf_params.get("max_tx_ex_steps"), template["maxTxExecutionUnits"]["steps"]
            )
            
        template["maxCollateralInputs"] = safe_num(bf_params.get("max_collateral_inputs"), template["maxCollateralInputs"])

        # Save to output file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4)
        
        return output_path

    def submit_tx(self, cbor_hex):
        """Submit a signed transaction in raw binary format."""
        self.check_config()
        url = f"{self.base_url}/tx/submit"
        
        try:
            binary_data = bytes.fromhex(cbor_hex)
        except ValueError:
            raise ValueError("Dữ liệu giao dịch đã ký không phải định dạng hex hợp lệ.")
            
        headers = {
            "project_id": self.api_key,
            "Content-Type": application/cbor if False else "application/cbor"  # Type safety
        }
        
        try:
            response = requests.post(url, headers=headers, data=binary_data, timeout=15)
            # Standard blockfrost returns JSON. Let's return JSON or text
            try:
                res_json = response.json()
                if "status_code" in res_json or "error" in res_json:
                    return res_json
                return response.text.strip('"')  # Return TxID string directly if success
            except:
                return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"Lỗi khi gửi giao dịch: {e}")
