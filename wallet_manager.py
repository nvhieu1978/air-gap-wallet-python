import os
import sys
import subprocess
import shutil
import tempfile
import json
import re

def secure_delete(path):
    """Securely overwrite and delete a file."""
    if not os.path.exists(path):
        return
    try:
        # If shred is available on system, use it (typically on Linux)
        if shutil.which("shred"):
            subprocess.run(["shred", "-u", "-n", "3", path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    except:
        pass
    
    # Python fallback secure deletion
    try:
        size = os.path.getsize(path)
        with open(path, "r+b") as f:
            for _ in range(3):
                f.seek(0)
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
        # Truncate to 0 bytes
        with open(path, "w") as f:
            f.write("")
        os.remove(path)
    except Exception as e:
        # Fallback to standard delete if secure overwrite fails
        try:
            os.remove(path)
        except:
            pass

class WalletManager:
    def __init__(self, config):
        self.config = config

    def get_secure_temp_dir(self):
        """Create a secure temporary directory in RAM if possible, or standard temp dir with strict permissions."""
        if sys.platform.startswith("linux") and os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK):
            # Linux RAM-disk
            temp_dir = tempfile.mkdtemp(prefix="cardano_airgap_tmp_", dir="/dev/shm")
        else:
            # Fallback temp directory
            temp_dir = tempfile.mkdtemp(prefix="cardano_airgap_tmp_")
            
        os.chmod(temp_dir, 0o700)
        return temp_dir

    def cleanup_temp_dir(self, temp_dir):
        """Securely shred all files inside a temp directory, and then remove the directory."""
        if not temp_dir or not os.path.exists(temp_dir):
            return
        try:
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    secure_delete(os.path.join(root, f))
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Lỗi khi dọn dẹp thư mục tạm: {e}")

    def get_envelope_type(self):
        """Parse cardano-cli version to determine transaction envelope type."""
        cli_path = self.config.get("cardano_cli_path") or "cardano-cli"
        try:
            res = subprocess.run([cli_path, "--version"], capture_output=True, text=True, check=True)
            first_line = res.stdout.splitlines()[0]
            match = re.search(r'cardano-cli\s+(\d+)', first_line)
            if match:
                major = int(match.group(1))
                if major < 9:
                    return "TxBodyConway"
            return "Tx ConwayEra"
        except Exception as e:
            print(f"Cảnh báo: Không thể xác định phiên bản cardano-cli ({e}). Sử dụng mặc định ConwayEra.")
            return "Tx ConwayEra"

    def list_wallets(self):
        """Return list of existing wallet names."""
        wallets_dir = "wallets"
        if not os.path.exists(wallets_dir):
            return []
        
        wallets = []
        for name in os.listdir(wallets_dir):
            path = os.path.join(wallets_dir, name)
            # Check for key encrypted files
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "payment.skey.enc")):
                wallets.append(name)
        return sorted(wallets)

    def generate_recovery_phrase(self):
        """Generate a 24-word BIP39 recovery phrase using cardano-address."""
        addr_path = self.config.get("cardano_address_path") or "cardano-address"
        try:
            res = subprocess.run(
                [addr_path, "recovery-phrase", "generate", "--size", "24"],
                capture_output=True, text=True, check=True
            )
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Lỗi khi gọi cardano-address để tạo cụm từ khôi phục: {e.stderr}")

    def create_wallet(self, wallet_name, password, phrase, progress_callback=None):
        """
        Create a new Cardano wallet or restore an existing one.
        Generates keys, address, and encrypts private files.
        """
        # Paths to executables
        cli_path = self.config.get("cardano_cli_path") or "cardano-cli"
        addr_path = self.config.get("cardano_address_path") or "cardano-address"
        network_args = self.config.network_param
        
        # Verify tools are executable
        if not shutil.which(cli_path):
            raise FileNotFoundError(f"Không tìm thấy cardano-cli tại: {cli_path}")
        if not shutil.which(addr_path):
            raise FileNotFoundError(f"Không tìm thấy cardano-address tại: {addr_path}")
            
        wallet_name = re.sub(r'[^a-zA-Z0-9_-]', '', wallet_name)
        if not wallet_name:
            raise ValueError("Tên ví không hợp lệ.")
            
        wallet_dir = os.path.abspath(os.path.join("wallets", wallet_name))
        os.makedirs(wallet_dir, exist_ok=True)
        
        temp_dir = self.get_secure_temp_dir()
        
        try:
            def update_progress(msg):
                if progress_callback:
                    progress_callback(msg)
                    
            # 1. Write phrase to temp RAM path
            phrase_path = os.path.join(temp_dir, "phrase.prv")
            with open(phrase_path, "w", encoding="utf-8") as f:
                f.write(phrase)
                
            update_progress("Đang khởi tạo khóa Root từ cụm từ khôi phục...")
            # 2. Root Key
            root_path = os.path.join(temp_dir, "root.prv")
            with open(root_path, "w") as out:
                subprocess.run(
                    [addr_path, "key", "from-recovery-phrase", "Shelley"],
                    input=phrase.encode("utf-8"),
                    stdout=out, check=True
                )
                
            update_progress("Đang khởi tạo khóa Payment (Thanh toán)...")
            # 3. Payment Private & Public keys
            pay_prv_path = os.path.join(temp_dir, "payment.prv")
            with open(root_path, "r") as r_file:
                with open(pay_prv_path, "w") as p_file:
                    subprocess.run(
                        [addr_path, "key", "child", "1852H/1815H/0H/0/0"],
                        stdin=r_file, stdout=p_file, check=True
                    )
                    
            pay_pub_path = os.path.join(wallet_dir, "payment.pub")
            with open(pay_prv_path, "r") as p_prv:
                with open(pay_pub_path, "w") as p_pub:
                    subprocess.run(
                        [addr_path, "key", "public", "--without-chain-code"],
                        stdin=p_prv, stdout=p_pub, check=True
                    )
                    
            # Convert Payment Key to cardano-cli signing key (.skey)
            pay_skey_path = os.path.join(temp_dir, "payment.skey")
            subprocess.run([
                cli_path, "key", "convert-cardano-address-key",
                "--shelley-payment-key",
                "--signing-key-file", pay_prv_path,
                "--out-file", pay_skey_path
            ], check=True)
            
            # Generate payment verification key (.vkey)
            pay_vkey_path = os.path.join(wallet_dir, "payment.vkey")
            subprocess.run([
                cli_path, "key", "verification-key",
                "--signing-key-file", pay_skey_path,
                "--verification-key-file", pay_vkey_path
            ], check=True)
            
            update_progress("Đang khởi tạo khóa Stake (Ủy quyền)...")
            # 4. Stake keys
            stake_prv_path = os.path.join(temp_dir, "stake.prv")
            with open(root_path, "r") as r_file:
                with open(stake_prv_path, "w") as s_file:
                    subprocess.run(
                        [addr_path, "key", "child", "1852H/1815H/0H/2/0"],
                        stdin=r_file, stdout=s_file, check=True
                    )
                    
            # Convert Stake key to cardano-cli format (.skey)
            stake_skey_path = os.path.join(temp_dir, "stake.skey")
            subprocess.run([
                cli_path, "key", "convert-cardano-address-key",
                "--shelley-stake-key",
                "--signing-key-file", stake_prv_path,
                "--out-file", stake_skey_path
            ], check=True)
            
            # Generate extended stake verification key (.vkey)
            ext_stake_vkey_path = os.path.join(temp_dir, "Ext_ShelleyStake.vkey")
            subprocess.run([
                cli_path, "key", "verification-key",
                "--signing-key-file", stake_skey_path,
                "--verification-key-file", ext_stake_vkey_path
            ], check=True)
            
            # Convert to standard non-extended stake verification key
            stake_vkey_path = os.path.join(wallet_dir, "stake.vkey")
            subprocess.run([
                cli_path, "key", "non-extended-key",
                "--extended-verification-key-file", ext_stake_vkey_path,
                "--verification-key-file", stake_vkey_path
            ], check=True)
            
            update_progress("Đang sinh địa chỉ ví thanh toán và ủy quyền...")
            # 5. Build addresses
            addr_pay_path = os.path.join(wallet_dir, "payment.addr")
            build_addr_cmd = [
                cli_path, "address", "build",
                "--payment-verification-key-file", pay_vkey_path,
                "--stake-verification-key-file", stake_vkey_path,
                "--out-file", addr_pay_path
            ] + network_args
            subprocess.run(build_addr_cmd, check=True)
            
            addr_stake_path = os.path.join(wallet_dir, "stake.addr")
            build_stake_cmd = [
                cli_path, "conway", "stake-address", "build",
                "--stake-verification-key-file", stake_vkey_path,
                "--out-file", addr_stake_path
            ] + network_args
            subprocess.run(build_stake_cmd, check=True)
            
            # Read payment address to return to UI
            with open(addr_pay_path, "r") as f:
                payment_addr = f.read().strip()
                
            # Read stake address to return
            with open(addr_stake_path, "r") as f:
                stake_addr = f.read().strip()
                
            update_progress("Đang mã hóa các tệp khóa bằng OpenSSL AES-256-CBC...")
            # 6. Encrypt sensitive keys
            # Encrypt payment.skey
            pay_enc_path = os.path.join(wallet_dir, "payment.skey.enc")
            subprocess.run([
                "openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2", "-iter", "100000",
                "-in", pay_skey_path, "-out", pay_enc_path, "-pass", f"pass:{password}"
            ], check=True)
            
            # Encrypt stake.skey
            stake_enc_path = os.path.join(wallet_dir, "stake.skey.enc")
            subprocess.run([
                "openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2", "-iter", "100000",
                "-in", stake_skey_path, "-out", stake_enc_path, "-pass", f"pass:{password}"
            ], check=True)
            
            # Encrypt mnemonic phrase
            phrase_enc_path = os.path.join(wallet_dir, "phrase.prv.enc")
            subprocess.run([
                "openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2", "-iter", "100000",
                "-in", phrase_path, "-out", phrase_enc_path, "-pass", f"pass:{password}"
            ], check=True)
            
            update_progress("Hoàn tất tạo ví thành công!")
            return payment_addr, stake_addr
            
        finally:
            self.cleanup_temp_dir(temp_dir)

    def sign_transaction(self, wallet_name, password, raw_cbor_hex, is_delegation=False, progress_callback=None):
        """
        Decrypt secret keys to RAM-disk temporarily and sign the raw CBOR transaction.
        """
        cli_path = self.config.get("cardano_cli_path") or "cardano-cli"
        network_args = self.config.network_param
        
        wallet_dir = os.path.abspath(os.path.join("wallets", wallet_name))
        pay_enc_path = os.path.join(wallet_dir, "payment.skey.enc")
        stake_enc_path = os.path.join(wallet_dir, "stake.skey.enc")
        
        if not os.path.exists(pay_enc_path):
            raise FileNotFoundError(f"Không tìm thấy khóa payment.skey.enc cho ví '{wallet_name}'")
            
        temp_dir = self.get_secure_temp_dir()
        
        try:
            def update_progress(msg):
                if progress_callback:
                    progress_callback(msg)
                    
            # 1. Structure the raw transaction JSON file in temp dir
            env_type = self.get_envelope_type()
            tx_raw_json = {
                "type": env_type,
                "description": "",
                "cborHex": raw_cbor_hex
            }
            tx_raw_path = os.path.join(temp_dir, "tx.raw")
            with open(tx_raw_path, "w") as f:
                json.dump(tx_raw_json, f, indent=4)
                
            update_progress("Đang giải mã khóa ký thanh toán...")
            # 2. Decrypt payment.skey to temp path
            pay_skey_tmp = os.path.join(temp_dir, "payment.skey.tmp")
            
            res = subprocess.run([
                "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "100000",
                "-in", pay_enc_path, "-out", pay_skey_tmp, "-pass", f"pass:{password}"
            ], capture_output=True)
            
            if res.returncode != 0 or not os.path.exists(pay_skey_tmp) or os.path.getsize(pay_skey_tmp) == 0:
                err_detail = res.stderr.decode('utf-8', errors='ignore').strip() if res.stderr else "Không có thêm chi tiết."
                raise ValueError(f"Mật khẩu giải mã ví không chính xác hoặc khóa bị hỏng.\nChi tiết lỗi OpenSSL: {err_detail}")
                
            # 3. Setup signing keys list
            sign_args = ["--signing-key-file", pay_skey_tmp]
            
            # 4. If transaction is a delegation/governance one, decrypt stake.skey
            if is_delegation:
                if not os.path.exists(stake_enc_path):
                    raise FileNotFoundError(f"Không tìm thấy stake.skey.enc nhưng đây là giao dịch ủy quyền.")
                    
                update_progress("Đang giải mã khóa ký stake...")
                stake_skey_tmp = os.path.join(temp_dir, "stake.skey.tmp")
                res = subprocess.run([
                    "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "100000",
                    "-in", stake_enc_path, "-out", stake_skey_tmp, "-pass", f"pass:{password}"
                ], capture_output=True)
                
                if res.returncode != 0 or not os.path.exists(stake_skey_tmp) or os.path.getsize(stake_skey_tmp) == 0:
                    err_detail = res.stderr.decode('utf-8', errors='ignore').strip() if res.stderr else "Không có thêm chi tiết."
                    raise ValueError(f"Không thể giải mã khóa stake. Mật khẩu có thể không đúng.\nChi tiết lỗi OpenSSL: {err_detail}")
                    
                sign_args.extend(["--signing-key-file", stake_skey_tmp])
                
            update_progress("Đang ký giao dịch bằng cardano-cli...")
            # 5. Call cardano-cli to sign
            tx_signed_path = os.path.join(temp_dir, "tx.signed")
            
            sign_cmd = [
                cli_path, "conway", "transaction", "sign"
            ] + sign_args + network_args + [
                "--tx-body-file", tx_raw_path,
                "--out-file", tx_signed_path
            ]
            
            subprocess.run(sign_cmd, check=True)
            
            # 6. Read signed transaction hex
            with open(tx_signed_path, "r") as f:
                signed_data = json.load(f)
                
            signed_cbor = signed_data.get("cborHex")
            if not signed_cbor:
                raise ValueError("Lỗi: File đã ký không chứa dữ liệu cborHex.")
                
            update_progress("Ký giao dịch thành công!")
            
            # Save signed tx to tx_signed.txt in wallet folder
            signed_file_path = os.path.join(wallet_dir, "tx_signed.txt")
            with open(signed_file_path, "w") as f:
                f.write(f"TxConway:{signed_cbor}")
                
            return signed_cbor
            
        finally:
            self.cleanup_temp_dir(temp_dir)
            
    def decrypt_mnemonic(self, wallet_name, password):
        """Decrypt and return the wallet recovery phrase."""
        wallet_dir = os.path.abspath(os.path.join("wallets", wallet_name))
        phrase_enc_path = os.path.join(wallet_dir, "phrase.prv.enc")
        
        if not os.path.exists(phrase_enc_path):
            raise FileNotFoundError("Không tìm thấy tệp khôi phục cụm từ đã mã hóa.")
            
        temp_dir = self.get_secure_temp_dir()
        temp_phrase_path = os.path.join(temp_dir, "phrase.tmp")
        
        try:
            res = subprocess.run([
                "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "100000",
                "-in", phrase_enc_path, "-out", temp_phrase_path, "-pass", f"pass:{password}"
            ], capture_output=True)
            
            if res.returncode != 0 or not os.path.exists(temp_phrase_path) or os.path.getsize(temp_phrase_path) == 0:
                raise ValueError("Mật khẩu giải mã không chính xác.")
                
            with open(temp_phrase_path, "r", encoding="utf-8") as f:
                phrase = f.read().strip()
                
            return phrase
        finally:
            self.cleanup_temp_dir(temp_dir)
