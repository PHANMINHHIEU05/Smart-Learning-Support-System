1. Tên dự án (Đề xuất)

Hệ thống Web hỗ trợ học tập thông minh dựa trên phân tích hành vi và cảm xúc người dùng. (Smart Learning Support System using Behavioral and Emotional Analytics) 2. Kiến trúc hệ thống (System Architecture)

Dự án được xây dựng theo mô hình Client-Server chuyên nghiệp:

    AI Engine (Client Side): Sử dụng Python (OpenCV, MediaPipe, DeepFace) để thu thập và xử lý tín hiệu sinh trắc học thời gian thực.

    Backend (Server Side): FastAPI hoặc Flask quản lý logic nghiệp vụ, tính toán điểm số và điều phối dữ liệu.

    Database: SQLite (phát triển) hoặc PostgreSQL (vận hành) thông qua SQLAlchemy ORM.

    Frontend Dashboard: Giao diện Web hiển thị thông số trực tiếp và biểu đồ thống kê lịch sử.

3. Các module tính năng cốt lõi (Core Modules)
   Module Công nghệ Nhiệm vụ chính
   Nhận diện trạng thái MediaPipe Face Mesh Tính chỉ số EAR (Mắt) để phát hiện buồn ngủ.
   Phân tích tư thế MediaPipe Pose Tính góc Pitch (Cúi đầu), Shoulder Level (Lệch vai/Gù lưng).
   Nhận diện cảm xúc DeepFace Phân tích tâm lý (Vui, buồn, chán nản, trung tính).
   Adaptive Logic Toán học/Thống kê Hiệu chỉnh (Calibration) để tạo ngưỡng động (Z-score) cho từng người.
   Data Mining Pandas/SQLAlchemy Gom nhóm dữ liệu, tìm ra quy luật tập trung theo thời gian.
4. Hàm lượng kỹ thuật "4 Tín chỉ" (Technical Depth)

Để dự án không bị coi là "bé", chúng ta tập trung vào 3 điểm nhấn kỹ thuật:

    Tính thích nghi (Adaptability): Hệ thống không dùng số chết (ví dụ: EAR < 0.2). Nó có bước 10 giây đầu để "học" đặc điểm người dùng và tự tính toán ngưỡng cảnh báo phù hợp.

    Xử lý đa luồng (Threading): Chạy song song MediaPipe (30 FPS) và DeepFace (0.3 FPS) để đảm bảo hệ thống mượt mà, không giật lag.

    Phân tích đa phương thức (Multi-modal): Kết hợp đồng thời 3 yếu tố: Mắt + Tư thế + Cảm xúc để đưa ra một chỉ số tập trung (Focus Score) duy nhất.

5. Cấu trúc cơ sở dữ liệu (Database Schema)

Đây là phần để "ghi điểm" với thầy Phương về mảng Data:

    Bảng Users: Thông tin tài khoản và cấu hình cá nhân.

    Bảng User_Profiles: Lưu các chỉ số Mean/Std (Trung bình/Độ lệch chuẩn) sau khi hiệu chỉnh.

    Bảng Study_Sessions: Lưu thông tin mỗi phiên học (Bắt đầu, kết thúc, điểm trung bình).

    Bảng Focus_Logs: Lưu dữ liệu chi tiết mỗi phút (Dạng Time-series) để vẽ biểu đồ.
