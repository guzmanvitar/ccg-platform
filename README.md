## 🔧 Setup & Installation
1️⃣ Clone the Repository
```bash
git clone ...
cd yt-style-retaining-translator
```

2️⃣ Install Dependencies
This repo uses [uv](https://docs.astral.sh/uv/getting-started/installation) to install and manage dependencies,
as well as to set up the Python environment. After installing `uv` run
```bash
uv python install 3.10.13
uv sync
```
To set up Git hooks for code quality checks run also
```bash
uv run pre-commit install
```
