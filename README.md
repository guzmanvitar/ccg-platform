# Carnivore Conservation Genomics Platform

A Django-based web platform for conservation research focused on carnivore species in South and Central America. This platform facilitates genetic data sharing, analysis, and geographic assignment tools for wildlife conservation efforts.

## 🎯 Project Overview

The Carnivore Conservation Genomics Platform aims to:

- **Create a common database** of genetic data (full sequence and SNPs)
- **Facilitate standardized SNP panels** for geographic assignment
- **Provide SNP-based tools** for geographic assignment of samples
- **Support ongoing research** and conservation efforts

## ✨ Features

### 🔐 Authentication & Security
- **OAuth Integration**: Google OAuth authentication via Django Allauth
- **Email Confirmation**: Mandatory email verification for all new accounts
- **Secure File Uploads**: Protected upload functionality for genetic data
- **Rate Limiting**: Prevents abuse with configurable rate limits

### 🧬 Genetic Data Management
- **Multi-format Support**: Upload VCF, FASTA, FASTQ, and TXT files
- **Species-specific Tools**: Currently supports Panthera onca (Jaguar)
- **File Organization**: Automatic organization by species and file format
- **User-specific Storage**: Isolated file storage per user

### 🛠️ Analysis Tools
- **Geographic Assignment**: SNP-based tools for sample origin determination
- **Data Visualization**: View uploaded files and analysis results
- **Research Integration**: Seamless workflow for conservation researchers

### 🎨 User Experience
- **Modern UI**: Clean, responsive design with IBM Plex Sans typography
- **Intuitive Navigation**: Easy-to-use interface for researchers
- **Mobile-friendly**: Responsive design for field research use

## 🔧 Setup & Installation

### Prerequisites
- Python 3.10.13
- [uv](https://docs.astral.sh/uv/getting-started/installation) package manager

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/guzmanvitar/ccg-platform.git
cd ccg-platform
```

### 2️⃣ Install Dependencies
This repo uses [uv](https://docs.astral.sh/uv/getting-started/installation) to install and manage dependencies,
as well as to set up the Python environment. After installing `uv` run:
```bash
uv python install 3.10.13
uv sync
```

### 3️⃣ Set Up Development Environment
To set up Git hooks for code quality checks run:
```bash
uv run pre-commit install
```

### 4️⃣ Database Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 5️⃣ Run Development Server
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

## 📧 Email Configuration

### Development
The platform is configured to use console email backend for development. Verification emails will appear in your terminal console.

### Production
To configure email sending for production, update the settings in `ccg_platform/settings.py`:

#### Gmail Example
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use App Password, not regular password
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

#### Other SMTP Providers
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@domain.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'your-email@domain.com'
```

## 🚀 Usage

### User Registration & Authentication
1. **Sign Up**: Create account with email and password
2. **Email Verification**: Check email and click verification link
3. **Login**: Access platform features with Google OAuth or email/password

### Genetic Data Upload
1. **Navigate to Species Tools**: Select "Panthera onca (Jaguar)"
2. **Upload Files**: Supported formats: VCF, FASTA, FASTQ, TXT
3. **File Management**: View and manage uploaded files
4. **Analysis**: Run geographic assignment tools

### Protected Features
- **File Upload**: Requires verified email address
- **Analysis Tools**: Access to geographic assignment features
- **Data Management**: View and organize uploaded genetic data

## 🏗️ Project Structure

```
ccg_platform/
├── ccg_platform/          # Main Django project settings
│   ├── settings.py        # Django configuration
│   ├── urls.py           # Main URL routing
│   └── templates/        # Global templates
│       └── account/      # Authentication templates
├── inference/            # Main application
│   ├── views.py         # View logic
│   ├── forms.py         # Form definitions
│   ├── urls.py          # App URL routing
│   └── templates/       # App templates
├── static/              # CSS, JS, and static files
├── manage.py           # Django management script
└── pyproject.toml      # Project dependencies
```

## 🔒 Security Features

- **Email Verification**: Mandatory email confirmation for all accounts
- **HMAC Links**: Secure email confirmation links
- **Rate Limiting**: 5 requests per minute for various actions
- **CSRF Protection**: Built-in Django CSRF protection
- **OAuth Security**: Secure Google OAuth integration

## 🧪 Testing

### Manual Testing
1. Start the development server: `python manage.py runserver`
2. Create a new account
3. Check the console output for the verification email
4. Click the verification link
5. Verify that you can access protected features

### Automated Testing
```bash
# Run tests
uv run pytest

# Code quality checks
uv run black .
uv run flake8
uv run isort .
```

## 🛠️ Development

### Code Quality
This project uses several tools to maintain code quality:
- **Black**: Code formatting
- **Flake8**: Linting
- **isort**: Import sorting
- **pre-commit**: Git hooks for quality checks

### Adding New Features
1. Create feature branch
2. Implement changes
3. Add tests
4. Run quality checks
5. Submit pull request

## 📚 Dependencies

### Core Dependencies
- **Django 5.2.3+**: Web framework
- **Django Allauth 65.9.0+**: Authentication system
- **Cryptography 45.0.4+**: Security utilities
- **PyJWT 2.10.1+**: JWT handling

### Development Dependencies
- **Black**: Code formatting
- **Flake8**: Linting
- **Pytest**: Testing framework
- **JupyterLab**: Development environment
- **pre-commit**: Git hooks

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is part of conservation research efforts by PUCRS's genomics lab.

## 🆘 Support

For issues and questions:
- Check the [EMAIL_CONFIRMATION_SETUP.md](EMAIL_CONFIRMATION_SETUP.md) for email configuration details
- Review Django and Django Allauth documentation
- Contact the development team

---

**Developed by**: PUCRS — Laboratório de Biologia Genômica e Molecular
