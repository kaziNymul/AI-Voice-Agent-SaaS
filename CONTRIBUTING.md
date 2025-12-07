# Contributing to AI Voice Customer Care SaaS

Thank you for considering contributing to this project! 🎉

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System info (OS, Docker version, Python version)
   - Relevant logs

### Suggesting Features

1. Open an issue with `[Feature Request]` prefix
2. Describe the feature and use case
3. Explain why it would benefit users

### Code Contributions

#### Getting Started

```bash
# Fork the repository
git clone https://github.com/yourusername/ai-voice-customer-care.git
cd ai-voice-customer-care

# Create a branch
git checkout -b feature/your-feature-name

# Make your changes
# ...

# Test your changes
./setup_ultralight_saas.sh
# Test the feature manually

# Commit with descriptive message
git commit -m "Add: Feature description"

# Push and create PR
git push origin feature/your-feature-name
```

#### Code Style

- **Python**: Follow PEP 8
- **Docstrings**: Use Google style
- **Type hints**: Use for function parameters and returns
- **Line length**: Max 100 characters
- **Imports**: Organize with isort

Example:
```python
from typing import Optional

async def process_audio(
    audio_bytes: bytes,
    language: Optional[str] = "en"
) -> str:
    """
    Process audio file and return transcription.
    
    Args:
        audio_bytes: Raw audio file bytes
        language: Language code (ISO 639-1)
    
    Returns:
        Transcribed text string
    
    Raises:
        AudioProcessingError: If transcription fails
    """
    # Implementation
    pass
```

#### Testing Guidelines

- Add tests for new features
- Ensure existing tests pass
- Test with both local and AWS configurations
- Test with different Docker configurations

#### Commit Messages

Use conventional commits:

```
feat: Add AWS Transcribe integration
fix: Resolve timeout issue in voice service
docs: Update installation guide
refactor: Simplify audio service logic
test: Add unit tests for RAG service
chore: Update dependencies
```

### Pull Request Process

1. **Update documentation** if needed (README, docstrings)
2. **Update CHANGELOG.md** with your changes
3. **Ensure CI passes** (if configured)
4. **Request review** from maintainers
5. **Address feedback** promptly

### Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements-ultralight.txt
pip install -r dev-requirements.txt  # Development tools

# Install pre-commit hooks
pre-commit install
```

### Project Structure

Understanding where to make changes:

```
app/
├── routes/          # Add new API endpoints here
├── services/        # Add new business logic services
├── clients/         # Add new external service integrations
├── models/          # Add new data models
└── utils/           # Add utility functions

saas_dashboard/      # Dashboard UI and admin features
voice_server.py      # Voice service (STT/TTS) modifications
```

### Areas We Need Help With

- 🌍 **Multi-language support** - Add support for non-English languages
- 📊 **Analytics** - Usage tracking and reporting dashboard
- 🧪 **Testing** - More unit and integration tests
- 📱 **Mobile app** - React Native or Flutter client
- ☁️ **Cloud providers** - GCP, Azure integrations
- 📚 **Documentation** - Tutorials, video guides
- 🎨 **UI/UX** - Dashboard improvements

### Questions?

- Open a [Discussion](https://github.com/yourusername/ai-voice-customer-care/discussions)
- Join our [Discord](https://discord.gg/yourserver) (if applicable)
- Email: your-email@example.com

---

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community

### Enforcement

Unacceptable behavior may result in:
1. Warning
2. Temporary ban
3. Permanent ban

Report issues to: your-email@example.com

---

Thank you for contributing! 🚀
