# 🛡️ Hướng Dẫn Sử Dụng Ví Lạnh Cardano Air-Gap Wallet

Chào mừng bạn đến với **Cardano Air-Gap Wallet** - giải pháp ví lạnh tự custody (tự quản lý) cực kỳ an toàn dành cho mạng lưới Cardano. 

Tài liệu này được viết riêng cho những người **không chuyên về kỹ thuật (non-tech)**. Chúng tôi sẽ giải thích mọi khái niệm bằng ngôn ngữ đơn giản nhất và hướng dẫn bạn từng bước để giao dịch an toàn tuyệt đối.

---

## 💡 Ví lạnh "Air-Gap" là gì? Tại sao nó an toàn nhất?

*   **Ví nóng (Online Wallet)**: Ví trên điện thoại hoặc máy tính kết nối Internet. Nếu máy tính của bạn bị nhiễm virus hoặc hacker xâm nhập, khóa bí mật (Private Key) có thể bị đánh cắp và bạn sẽ mất hết tiền.
*   **Ví lạnh "Air-Gap" (Không kết nối)**: Là phương pháp sử dụng **hai thiết bị riêng biệt**:
    1.  **Máy Offline (Máy Ký - Ví Lạnh)**: Một chiếc máy tính cũ/không bao giờ kết nối Internet (không có Wifi, không cắm dây mạng). Thiết bị này giữ khóa bí mật của bạn.
    2.  **Máy Online (Máy Xem/Gửi)**: Máy tính sử dụng hàng ngày có kết nối mạng. Máy này chỉ dùng để xem số dư, soạn giao dịch và gửi giao dịch lên mạng lưới, hoàn toàn không biết khóa bí mật của bạn là gì.
*   **Truyền dữ liệu bằng mã QR**: Thay vì cắm USB (có nguy cơ lây truyền mã độc giữa máy Online và Offline), bạn chỉ cần **dùng Camera để quét mã QR** giữa hai màn hình máy tính. Cực kỳ an toàn và tiện lợi!

---

## 🛠️ Chuẩn Bị & Cài Đặt (Chỉ cần làm một lần)

### 1. Cài đặt Python, Tạo Môi Trường Ảo (venv) & Cài Thư Viện Phụ Thuộc
Để ứng dụng chạy ổn định và tránh xung đột thư viện với hệ thống, bạn nên tạo một **Môi trường ảo (Virtual Environment - venv)**:

*   **Trên Linux (Ubuntu/Debian)**:
    Mở ứng dụng Terminal lên và chạy các lệnh sau:
    ```bash
    # 1. Cài đặt Python 3, venv và các công cụ hệ thống
    sudo apt-get update
    sudo apt-get install python3 python3-pip python3-venv python3-pil python3-pil.imagetk qrencode zbar-tools -y

    # 2. Tạo môi trường ảo
    python3 -m venv venv

    # 3. Kích hoạt môi trường ảo
    source venv/bin/activate

    # 4. Cài đặt các thư viện cần thiết
    pip install -r requirements.txt
    ```

*   **Trên Windows / macOS**:
    1. Tải và cài đặt [Python 3](https://www.python.org/downloads/). (Nhớ tích chọn **"Add Python to PATH"** khi cài đặt).
    2. Mở Command Prompt / Terminal và chạy:
       ```bash
       # 1. Tạo môi trường ảo
       python -m venv venv

       # 2. Kích hoạt môi trường ảo:
       # - Trên Windows (Command Prompt):
       venv\Scripts\activate
       # - Trên macOS / Linux:
       source venv/bin/activate

       # 3. Cài đặt các thư viện cần thiết
       pip install -r requirements.txt
       ```

### 2. Tải các công cụ Cardano Binaries (`cardano-cli` & `cardano-address`)
Để ký giao dịch và tạo địa chỉ ví lạnh, chương trình cần sử dụng các công cụ dòng lệnh chính thức từ hệ sinh thái Cardano. Bạn hãy tải chúng về máy:

*   **cardano-cli** (Công cụ giao dịch Cardano):
    1. Truy cập trang phát hành chính thức: [IntersectMBO/cardano-node Releases](https://github.com/IntersectMBO/cardano-node/releases).
    2. Cuộn xuống phần **Assets** của phiên bản mới nhất (ví dụ: v9.0.0 hoặc mới hơn).
    3. Tải phiên bản tương thích với hệ điều hành của bạn:
       *   **Linux**: Tải file `cardano-node-<phiên_bản>-linux.tar.gz` (giải nén ra sẽ có file `cardano-cli` bên trong).
       *   **macOS**: Tải file `cardano-node-<phiên_bản>-macos.tar.gz` (hoặc phiên bản tương ứng cho chip M1/M2/Intel).
       *   **Windows**: Tải file `cardano-node-<phiên_bản>-windows.zip`.
*   **cardano-address** (Công cụ sinh địa chỉ từ 24 từ khóa):
    1. Truy cập trang phát hành: [IntersectMBO/cardano-addresses Releases](https://github.com/IntersectMBO/cardano-addresses/releases).
    2. Vào phiên bản mới nhất, tải file tương ứng dưới mục **Assets** (ví dụ: `cardano-addresses-<phiên_bản>-linux64.tar.gz` cho Linux, hoặc `.zip` cho Windows/macOS).
    3. Giải nén để lấy file thực thi `cardano-address` (hoặc `cardano-address.exe` trên Windows).

*Sau khi tải xong, hãy nhớ đường dẫn thư mục chứa 2 file này để điền vào phần **Cài đặt** của ứng dụng ở bước tiếp theo.*

### 3. Tải và chạy ứng dụng
Tải toàn bộ thư mục code về máy, mở thư mục đó trong terminal và gõ:
```bash
python3 main.py
```

---

## ⚙️ Thiết Lập Ban Đầu (Tại tab "Cài Đặt")

Khi mở ứng dụng lần đầu tiên, hãy nhấn vào tab **Cài Đặt** ở thanh bên trái để thiết lập kết nối mạng:

1.  **Mạng / Network**: Chọn **Mainnet** (Mạng chạy tiền thật) hoặc **Preprod** (Mạng thử nghiệm/testnet).
2.  **Blockfrost Base URL**: Hệ thống sẽ tự động điền địa chỉ API tương ứng theo mạng bạn chọn.
3.  **Blockfrost API Key**: Đăng ký một tài khoản miễn phí tại [Blockfrost.io](https://blockfrost.io/) để lấy khóa API, giúp ví của bạn kết nối và lấy dữ liệu số dư từ Blockchain Cardano. Dán khóa này vào ô.
4.  **Đường dẫn Cardano Binaries**: Nếu bạn đã có `cardano-cli` và `cardano-address`, hãy nhấn **Browse** để trỏ tới tệp đó. Nếu chưa có, chương trình sẽ cố gắng tự động tìm trong hệ thống của bạn.
5.  Nhấn **Lưu Cài Đặt**.

### 🔑 Hướng dẫn lấy Blockfrost API Key và cách lưu trữ
Để ví của bạn có thể đọc số dư (UTXO) và gửi giao dịch trực tiếp lên mạng lưới Cardano, bạn cần có một khóa kết nối gọi là **Blockfrost API Key**.

**Cách lấy khóa API**:
1. Truy cập vào trang web [Blockfrost.io](https://blockfrost.io/) và đăng ký một tài khoản miễn phí.
2. Đăng nhập và đi đến phần **Dashboard (Bảng điều khiển)**.
3. Chọn **Add Project (Thêm dự án)**:
   * Nếu bạn chọn mạng chạy tiền thật, hãy chọn mạng **Cardano Mainnet**.
   * Nếu muốn thử nghiệm bằng tiền ảo miễn phí, hãy chọn mạng **Cardano Preprod**.
4. Sau khi tạo dự án, bạn sẽ thấy một chuỗi ký tự dài bắt đầu bằng `mainnet...` hoặc `preprod...`. Đó chính là **API Key** của bạn. Hãy sao chép nó.

**Lưu trữ ở đâu?**
Có 2 cách để dán và lưu khóa này:
* **Cách 1 (Khuyên dùng)**: Mở phần mềm lên, chuyển sang tab **Cài Đặt**, dán khóa vào ô **Blockfrost API Key** rồi nhấn **Lưu Cài Đặt**. Phần mềm sẽ tự động tạo ra tệp `config.json` để lưu lại cho lần sau.
* **Cách 2**: Bạn có thể mở trực tiếp tệp `config.json` ở thư mục gốc của ví (nếu phần mềm đã khởi động ít nhất một lần) và điền trực tiếp giá trị vào mục `"blockfrost_api_key"`.

> [!WARNING]
> **CẢNH BÁO BẢO MẬT**: Tệp `config.json` chứa API Key của bạn, và thư mục `wallets/` chứa khóa bảo mật ví của bạn. Chúng tôi đã thiết lập tệp cấu hình `.gitignore` để ngăn chặn việc tải các tệp này lên GitHub. **Tuyệt đối không được xóa `.gitignore` hoặc cố ý tải các tệp này lên mạng công cộng.**

---

## 📋 Quy Trình 4 Bước Giao Dịch An Toàn Tuyệt Đối

> [!IMPORTANT]
> **Máy Offline** (Ví Lạnh) dùng để **Tạo ví (Bước 1)** và **Ký giao dịch (Bước 3)**.
> **Máy Online** dùng để **Xem UTXO/Soạn giao dịch (Bước 2)** và **Gửi giao dịch (Bước 4)**.

---

### 🟢 BƯỚC 1: Tạo hoặc Khôi Phục Ví (Thực hiện trên máy OFFLINE)

1.  Mở ứng dụng trên máy **Offline**, chọn tab **Ví của tôi**.
2.  Nhấn nút **Tạo / Khôi phục ví**.
3.  Nhập tên ví (ví dụ: `my_cold_wallet`).
4.  Lựa chọn:
    *   **Tạo ví mới**: Ứng dụng sẽ hiển thị **24 từ khóa khôi phục tiếng Anh**. Hãy ghi chép 24 từ này cẩn thận ra giấy và cất giữ ở nơi an toàn. *Tuyệt đối không chụp ảnh hoặc lưu trên máy tính kết nối mạng.*
    *   **Khôi phục ví**: Nhập lại 24 từ khóa cũ của bạn.
5.  Đặt một **Mật khẩu ví** mạnh để mã hóa file khóa bí mật. Nhấn xác nhận.
6.  Ứng dụng sẽ tạo ra:
    *   Địa chỉ ví công khai (tệp `payment.addr`): Bạn có thể gửi ADA vào địa chỉ này.
    *   Khóa bí mật đã được mã hóa bằng mật khẩu của bạn (`payment.skey.enc`). Bạn không bao giờ được chia sẻ tệp này cho ai.

---

### 🔵 BƯỚC 2: Soạn Giao Dịch (Thực hiện trên máy ONLINE)

Để chuyển tiền đi, bạn cần soạn một giao dịch nháp (Giao dịch chưa ký):

1.  Vào tab **Giao dịch Online** -> mục **1. Xây dựng Giao dịch**.
2.  Nhập địa chỉ ví của bạn (hoặc chọn ví từ danh sách nếu bạn đã đồng bộ địa chỉ sang máy Online).
3.  Nhấn **Tải số dư & UTXO**. Ví sẽ lấy danh sách các số dư hiện tại của bạn từ blockchain.
4.  **Địa chỉ nhận**: Nhập địa chỉ ví người nhận.
5.  **Số lượng gửi (ADA)**: Nhập số lượng ADA bạn muốn chuyển đi.
6.  *(Tùy chọn)* Nếu muốn ủy thác (Delegate) để nhận lãi stake ADA:
    *   Tích chọn **Ủy thác**.
    *   Chọn **DRep** mong muốn (Ví dụ: `C2VN` để ủng hộ cộng đồng Việt Nam, hoặc `Abstain`/`No Confidence`).
    *   Nhập mã **Stake Pool** mà bạn muốn gửi.
7.  Nhấn **Xây dựng giao dịch thô**.
8.  Màn hình sẽ hiển thị thông tin phí giao dịch, đồng thời tạo ra một **Mã QR giao dịch nháp**. 
9.  Nhấn nút **Copy Hex CBOR** hoặc lưu mã QR này về máy.

---

### 🟡 BƯỚC 3: Ký Giao Dịch (Thực hiện trên máy OFFLINE)

Bước này xác nhận bạn đồng ý chuyển số tiền trên bằng cách dùng khóa bí mật để ký:

1.  Mở ứng dụng trên máy **Offline**, vào tab **Ký Ngoại Tuyến**.
2.  Nhập nội dung giao dịch nháp thu được từ Bước 2:
    *   **Cách an toàn nhất**: Nhấn **Quét QR Camera** trên máy Offline, sau đó hướng camera vào màn hình máy Online đang hiển thị mã QR giao dịch nháp ở Bước 2.
    *   Cách khác: Tải ảnh QR vào máy Offline và nhấn **Đọc QR từ ảnh**, hoặc copy chuỗi Hex và paste vào ô nhập liệu bên trái.
3.  Chọn đúng ví của bạn ở ô **Chọn Ví Ký**.
4.  Nhập **Mật khẩu ví** bạn đã tạo ở Bước 1.
5.  Nhấn **Ký Giao Dịch**.
6.  Chương trình sẽ tự động giải mã tạm thời khóa bí mật trong bộ nhớ RAM (không ghi xuống ổ cứng), ký xác nhận giao dịch và tạo ra **Mã QR giao dịch đã ký**.
7.  Màn hình máy Offline sẽ hiển thị mã QR mới này.

---

### 🔴 BƯỚC 4: Gửi Giao Dịch Lên Blockchain (Thực hiện trên máy ONLINE)

Bây giờ bạn đưa giao dịch đã được ký trở lại máy Online để phát sóng lên blockchain:

1.  Mở máy **Online**, vào tab **Giao dịch Online** -> mục **2. Gửi Giao dịch đã ký**.
2.  Nhấn nút **Quét QR Camera** trên máy Online và hướng camera vào màn hình máy Offline để đọc mã QR giao dịch đã ký thu được ở Bước 3 (hoặc tải tệp `tx_signed.txt` đã được copy qua).
3.  Nhấn **Gửi giao dịch (Submit)**.
4.  Hệ thống sẽ gửi giao dịch lên mạng blockchain Cardano thông qua cổng Blockfrost. Khi thành công, màn hình sẽ hiển thị mã **Transaction ID (TxID)** màu xanh lá. Giao dịch của bạn đã hoàn tất!

---

## 🛡️ Các Nguyên Tắc Bảo Mật "Cốt Lõi"

1.  **Không bao giờ kết nối máy Offline vào Internet**: Kể cả khi cài đặt phần mềm xong, hãy rút vĩnh viễn dây mạng và tắt Wifi của máy Offline.
2.  **Khôi phục từ giấy**: 24 từ khôi phục là tài sản duy nhất của bạn. Nếu mất máy tính, bạn vẫn có thể dùng 24 từ này để lấy lại tiền. Hãy cất giữ bản giấy thật kỹ, tránh ẩm ướt hoặc hỏa hoạn.
3.  **Hạn chế dùng USB**: Phương pháp Quét QR là phương thức an toàn nhất để chuyển dữ liệu giữa 2 máy vì mã độc không thể lây lan qua hình ảnh.

Chúc bạn có những trải nghiệm tự quản lý tài sản an toàn và bảo mật tuyệt đối cùng Cardano Cold Wallet!

---

## ⚠️ Miễn Trừ Trách Nhiệm (Disclaimer)

*   **Cung cấp "Như hiện trạng" (As-Is)**: Phần mềm này được cung cấp hoàn toàn miễn phí, dưới dạng mã nguồn mở "như hiện trạng" mà không có bất kỳ sự đảm bảo hay bảo hành nào (dù trực tiếp hay gián tiếp) về tính hoạt động ổn định hay tính bảo mật tuyệt đối.
*   **Trách nhiệm tự quản lý khóa**: Bạn hoàn toàn chịu trách nhiệm bảo quản 24 từ khóa khôi phục (seed phrase), tệp mã hóa khóa bí mật (`.enc`) và mật khẩu ví của mình. Nếu bạn làm mất các thông tin này, **không ai có thể giúp bạn khôi phục lại tài sản**.
*   **Trách nhiệm tổn thất tài chính**: Các tác giả và nhà phát triển dự án này sẽ không chịu bất kỳ trách nhiệm pháp lý nào đối với mọi tổn thất, mất mát tài sản (ADA và các token khác), lỗi giao dịch do gửi sai địa chỉ, rò rỉ khóa bí mật do môi trường máy tính của người dùng bị hack, hoặc bất kỳ thiệt hại trực tiếp/gián tiếp nào phát sinh từ việc sử dụng phần mềm này.
*   **Khuyến nghị thử nghiệm**: Luôn khuyến khích thử nghiệm tạo, ký và gửi các giao dịch với số lượng ADA rất nhỏ trên mạng thử nghiệm (**Preprod/Preview**) để làm quen và kiểm tra tính chính xác của quy trình trước khi giao dịch tài sản thực tế trên mạng **Mainnet**.

