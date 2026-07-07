import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import tempfile
import shutil

# Add parent dir to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import AppConfig
from blockfrost_api import BlockfrostAPI
from wallet_manager import WalletManager, secure_delete
from transaction_builder import TransactionBuilder

class TestAppConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def test_default_config(self):
        with patch("config.CONFIG_FILE", self.config_path):
            config = AppConfig()
            self.assertEqual(config.get("network_magic"), 2) # default Preprod
            self.assertEqual(config.network_param, ["--testnet-magic", "2"])
            
    def test_set_and_get(self):
        with patch("config.CONFIG_FILE", self.config_path):
            config = AppConfig()
            config.set("network_magic", 1) # Mainnet
            self.assertEqual(config.get("network_magic"), 1)
            self.assertEqual(config.network_param, ["--mainnet"])
            
            # Check file persistence
            config2 = AppConfig()
            self.assertEqual(config2.get("network_magic"), 1)

class TestBlockfrostAPI(unittest.TestCase):
    @patch("requests.get")
    def test_get_utxos(self, mock_get):
        # Mock response from Blockfrost
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "tx_hash": "abcdef123456",
                "tx_index": 0,
                "amount": [{"unit": "lovelace", "quantity": "10000000"}]
            }
        ]
        mock_get.return_value = mock_response
        
        api = BlockfrostAPI("dummy_key", "https://cardano-preprod.blockfrost.io/api/v0")
        utxos = api.get_utxos("addr_test1dummy")
        
        self.assertEqual(len(utxos), 1)
        self.assertEqual(utxos[0]["tx_hash"], "abcdef123456")
        self.assertEqual(utxos[0]["amount"][0]["quantity"], "10000000")

class TestWalletManager(unittest.TestCase):
    def setUp(self):
        self.temp_workspace = tempfile.mkdtemp()
        # Patch config
        self.mock_config = MagicMock()
        self.mock_config.get.side_effect = lambda key: {
            "cardano_cli_path": "cardano-cli",
            "cardano_address_path": "cardano-address",
            "network_magic": 2
        }.get(key)
        self.mock_config.network_param = ["--testnet-magic", "2"]
        
    def tearDown(self):
        shutil.rmtree(self.temp_workspace)
        
    def test_secure_delete(self):
        test_file = os.path.join(self.temp_workspace, "test.txt")
        with open(test_file, "w") as f:
            f.write("sensitive secret info")
            
        self.assertTrue(os.path.exists(test_file))
        secure_delete(test_file)
        self.assertFalse(os.path.exists(test_file))

    @patch("subprocess.run")
    def test_generate_recovery_phrase(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13 word14 word15 word16 word17 word18 word19 word20 word21 word22 word23 word24\n"
        mock_run.return_value = mock_proc
        
        wm = WalletManager(self.mock_config)
        phrase = wm.generate_recovery_phrase()
        self.assertTrue(phrase.startswith("word1"))
        self.assertEqual(len(phrase.split()), 24)

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_create_wallet_keys_and_encryption(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/mock"
        mock_run.return_value = MagicMock(returncode=0)
        
        wm = WalletManager(self.mock_config)
        
        # Override wallets dir path inside test context to avoid mutating local wallets/ folder
        with patch("os.path.abspath") as mock_abs:
            mock_abs.side_effect = lambda p: p.replace("wallets", os.path.join(self.temp_workspace, "wallets"))
            
            # Create a mock wallet files before reading them in create_wallet
            wallet_name = "test_wallet"
            target_wallet_dir = os.path.join(self.temp_workspace, "wallets", wallet_name)
            os.makedirs(target_wallet_dir, exist_ok=True)
            
            with open(os.path.join(target_wallet_dir, "payment.addr"), "w") as f:
                f.write("addr_test1payment")
            with open(os.path.join(target_wallet_dir, "stake.addr"), "w") as f:
                f.write("addr_test1stake")
                
            pay_addr, stake_addr = wm.create_wallet(
                wallet_name=wallet_name,
                password="securepass123",
                phrase="word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13 word14 word15 word16 word17 word18 word19 word20 word21 word22 word23 word24"
            )
            
            self.assertEqual(pay_addr, "addr_test1payment")
            self.assertEqual(stake_addr, "addr_test1stake")

if __name__ == "__main__":
    unittest.main()
