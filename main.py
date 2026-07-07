#!/usr/bin/env python3
import os
import sys

def main():
    # Make sure wallets directory exists
    os.makedirs("wallets", exist_ok=True)
    
    # Run the Tkinter GUI app
    try:
        from gui import AirGapWalletApp
        app = AirGapWalletApp()
        app.mainloop()
    except ImportError as e:
        print(f"Error: Required dependency missing. Please check requirements: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to start Air-Gap Wallet application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
