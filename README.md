
# eXtended Parameter Designer (XPD)

eXtended Parameter Designer (XPD) is a graphical user interface tool for configuring and managing parameters of Infineon-style e-bike controllers. This project has been converted from Python 2 to Python 3 to ensure compatibility with modern systems.

## Features
- Configure and manage e-bike controller parameters.
- Support for various Infineon controller models.
- Upload and download profiles to/from controllers.
- Graphical interface built using PyGTK.

## Requirements
- Windows 11
- Python 3.x
- GTK+ for Windows
- PyGTK
- PySerial

## Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/Eliminater74/eXtended-Parameter-Designer.git
   cd eXtended-Parameter-Designer
   ```

2. **Install Python dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Install GTK+ for Windows:**
   - Download and install the GTK+ runtime from [GTK+ for Windows](https://gtk.org/download/windows.php).

4. **Install PyGTK for Windows:**
   - Download and install the PyGTK package for Windows.

## Running the Application

To run the application, execute the main script:
```sh
python xpd.pyw
```

## Converting Python Scripts to Executable

You can convert the Python scripts to an executable using PyInstaller:
1. Install PyInstaller:
   ```sh
   pip install pyinstaller
   ```

2. Create the executable:
   ```sh
   pyinstaller --onefile xpd.pyw
   ```

The executable will be generated in the `dist` folder.

## Usage
1. **Run the application:**
   - Execute `xpd.pyw` to open the graphical user interface.

2. **Set up environment:**
   - Use the `gettext_windows` module to set up localization if needed.

3. **Configure profiles:**
   - Load, edit, and save profiles using the GUI.

4. **Upload/download profiles:**
   - Use the provided options in the GUI to upload or download profiles to/from your e-bike controller.

## Contribution
Feel free to fork the repository and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
