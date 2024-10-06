# Attendance Management System Using Face Recognition

**Attendance Using Face Recognition** is a Python-based project that automates attendance tracking in educational institutions using facial recognition technology. This system offers a fast, secure, and efficient way to manage attendance records for both students and staff members.

## Table of Contents
- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Features
- **Face Recognition**: Automatically recognize and record attendance based on facial images.
- **Real-time Attendance**: Mark attendance as students or faculty members check in and out.
- **Admin Panel**: Manage users, attendance records, and generate attendance reports.
- **Secure and Efficient**: Reduces manual errors and ensures that attendance is recorded accurately.
- **Responsive Web Interface**: Manage and view attendance data via a Django-based web interface.

## Technologies Used
- **Python 3.8.x**
- **OpenCV**: For capturing and processing facial images.
- **dlib**: For face detection and recognition.
- **Django**: Web framework used to create the interface and handle database interactions.
- **SQLite**: Lightweight database to store user and attendance data.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ShadowAniket/Attendance_using_Face_Recognition.git
   cd Attendance_using_Face_Recognition
   ```

2. **Set up the virtual environment:**
   ```bash
   python3 -m venv env      # On Windows: py -3.8 -m venv .venv
   source env/bin/activate  # On Windows: .\.venv\Scripts\activate
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database:**
   ```bash
   python manage.py migrate
   ```

5. **Run the server:**
   ```bash
   python manage.py runserver
   ```
   Open your browser and go to `http://127.0.0.1:8000/` to access the system.

## Usage

1. **Admin Panel Access**:
   - Visit `http://127.0.0.1:8000/admin/` to log in as an admin and manage users and attendance records.
   
2. **Attendance Capture**:
   - Use the web interface to capture faces through a connected camera.
   - The system will automatically recognize the face and record attendance for the recognized individual.

3. **Generating Reports**:
   - Use the admin panel to generate and download attendance reports filtered by date, user, or department.

## Contributing

We welcome contributions! Please check out the [Contributing Guidelines](CONTRIBUTING.md) for more details on how to get started.

### Steps to Contribute:
1. Fork the repository.
2. Create a new feature branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature-name`).
5. Open a Pull Request.

For more detailed guidelines, see the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
