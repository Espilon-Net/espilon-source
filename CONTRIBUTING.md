# Contributing to Espilon

Thank you for your interest in contributing to Espilon! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Security Contributions](#security-contributions)
- [Community](#community)

---

## Code of Conduct

### Our Standards

- **Be respectful**: Treat everyone with respect and kindness
- **Be collaborative**: Work together to improve the project
- **Be responsible**: This is a security tool - use it ethically
- **Be professional**: Maintain professional communication
- **Be patient**: Help newcomers learn and grow

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Sharing malicious code or exploits for illegal purposes
- Unauthorized testing against third-party systems
- Trolling, insulting, or derogatory comments
- Publishing others' private information

**Violations**: Please report to project maintainers. Serious violations may result in being banned from the project.

---

## How Can I Contribute?

### Reporting Bugs

**Before submitting a bug report**:
1. Check the [documentation](docs/) for common issues
2. Search [existing issues](https://github.com/yourusername/epsilon/issues) to avoid duplicates
3. Try to reproduce with the latest version

**Good bug reports include**:
- Clear, descriptive title
- Steps to reproduce the issue
- Expected vs actual behavior
- ESP32 variant and board type
- ESP-IDF version
- Configuration (`sdkconfig` relevant parts)
- Serial output/logs
- Screenshots (if applicable)

**Bug Report Template**:
```markdown
## Description
[Clear description of the bug]

## Steps to Reproduce
1. Configure device with...
2. Execute command...
3. Observe error...

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- ESP32 Variant: ESP32/ESP32-S2/ESP32-S3/etc.
- Board: DevKit/ESP32-CAM/Custom
- ESP-IDF Version: v5.3.2
- Espilon Version: commit hash or version

## Logs
```
[Paste relevant logs here]
```

## Additional Context
[Any other relevant information]
```

### Suggesting Features

**Feature requests should**:
- Have a clear use case
- Align with project goals (security research/education)
- Consider resource constraints (ESP32 limitations)
- Include implementation ideas (if possible)

**Feature Request Template**:
```markdown
## Feature Description
[Clear description of the proposed feature]

## Use Case
[Why is this feature needed? What problem does it solve?]

## Proposed Implementation
[How could this be implemented? Consider:]
- Memory requirements
- CPU usage
- Network bandwidth
- Module structure
- Configuration options

## Alternatives Considered
[Other approaches you've thought about]

## Additional Context
[Mockups, examples, references]
```

### Contributing Code

**Types of contributions welcome**:

- Bug fixes
- New modules or commands
- Documentation improvements
- Code quality improvements (refactoring, optimization)
- Tests and test infrastructure
- Security enhancements
- Translations
- Tool improvements (C2, flasher, etc.)

**Getting started**:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## Development Setup

### Prerequisites

- ESP-IDF v5.3.2 or compatible
- Python 3.8+
- Git
- ESP32 development board (for testing)

### Fork and Clone

```bash
# Fork repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/epsilon.git
cd epsilon

# Add upstream remote
git remote add upstream https://github.com/original-owner/epsilon.git
```

### Set Up Development Environment

```bash
# Install ESP-IDF
cd ~/esp
git clone --recursive --branch v5.3.2 https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32
. ./export.sh

# Install Python dependencies (for C2)
cd /path/to/epsilon/tools/c2
pip3 install -r requirements.txt
```

### Create Feature Branch

```bash
# Update your fork
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

**Branch naming conventions**:
- `feature/feature-name` - New features
- `fix/bug-description` - Bug fixes
- `docs/topic` - Documentation updates
- `refactor/component-name` - Code refactoring
- `test/test-description` - Test additions

---

## Coding Standards

### C Code (ESP32 Firmware)

**Style Guide**:
- **Indentation**: 4 spaces (NO tabs)
- **Braces**: K&R style (opening brace on same line)
- **Naming**:
  - Functions: `snake_case` (e.g., `process_command`)
  - Variables: `snake_case` (e.g., `device_id`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_BUFFER_SIZE`)
  - Macros: `UPPER_SNAKE_CASE`
  - Structs: `snake_case_t` (e.g., `command_t`)

**Example**:
```c
#include "esp_log.h"
#include "utils.h"

#define TAG "MODULE"
#define MAX_RETRIES 3

typedef struct {
    char name[32];
    int value;
} config_t;

static int process_data(const uint8_t *data, size_t len)
{
    if (data == NULL || len == 0) {
        ESP_LOGE(TAG, "Invalid parameters");
        return -1;
    }

    for (size_t i = 0; i < len; i++) {
        // Process data
    }

    return 0;
}
```

**Best Practices**:
- Use ESP_LOG* macros for logging (not printf)
- Check return values and handle errors
- Free allocated memory (no leaks)
- Use const for read-only parameters
- Validate input parameters
- Document complex logic with comments
- Keep functions small and focused
- No global mutable state (use static or pass context)
- No magic numbers (use named constants)
- No commented-out code (use git history)

### Python Code (C2 Server)

**Style Guide**: [PEP 8](https://pep8.org/)
- **Indentation**: 4 spaces
- **Line length**: 100 characters max
- **Naming**:
  - Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private: `_leading_underscore`

**Example**:
```python
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class DeviceManager:
    """Manages connected ESP32 devices."""

    def __init__(self):
        self._devices = {}

    def add_device(self, device_id: str, connection) -> None:
        """Add a new device to the registry."""
        if not device_id:
            raise ValueError("device_id cannot be empty")

        self._devices[device_id] = connection
        logger.info(f"Device added: {device_id}")

    def get_device(self, device_id: str) -> Optional[object]:
        """Retrieve device by ID."""
        return self._devices.get(device_id)
```

**Best Practices**:
- Type hints for function signatures
- Docstrings for classes and public functions
- Use logging module (not print statements)
- Handle exceptions appropriately
- Use context managers (`with` statements)
- Run `black` for formatting
- Run `flake8` for linting

**Tools**:
```bash
# Format code
black tools/c2/

# Check style
flake8 tools/c2/

# Type checking
mypy tools/c2/
```

### Documentation

**Markdown Style**:
- Use ATX-style headers (`#`, `##`, `###`)
- Code blocks with language specifiers
- Tables for structured data
- Lists for sequential or unordered items

**Code Comments**:
- Explain **why**, not **what** (code shows what)
- Keep comments up-to-date with code
- Use TODO/FIXME/NOTE for temporary notes
- Remove obsolete comments

---

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Add or modify tests
- `chore`: Build system, dependencies, etc.

**Scope** (optional): Module or component affected
- `core`, `mod_network`, `mod_fakeap`, `c2`, `docs`, etc.

**Examples**:
```
feat(mod_network): add ARP scanning functionality

Implements ARP scanner with batch processing to discover
devices on local network. Scans /24 subnet in ~30 seconds.

Closes #42

---

fix(core): prevent memory leak in crypto module

Free allocated buffer after Base64 encoding.
Fixes memory leak that caused crashes after ~1000 messages.

Fixes #55

---

docs(install): add GPRS setup instructions

Adds detailed wiring diagrams and configuration steps
for SIM800 module integration.
```

**Rules**:
- Subject line: 50 characters or less
- Subject: Imperative mood ("add" not "added" or "adds")
- Subject: Lowercase (except proper nouns)
- Subject: No period at end
- Body: Wrap at 72 characters
- Body: Explain what and why (not how)
- Footer: Reference issues (Closes #123, Fixes #456)

---

## Pull Request Process

### Before Submitting

**Checklist**:
- [ ] Code follows style guide
- [ ] All tests pass (if applicable)
- [ ] New code has comments
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow guidelines
- [ ] Branch is up-to-date with upstream main
- [ ] No merge conflicts
- [ ] Tested on actual hardware (for firmware changes)

### Testing

**For firmware changes**:
```bash
cd espilon_bot
idf.py build
idf.py flash
idf.py monitor
# Verify functionality
```

**For C2 changes**:
```bash
cd tools/c2
python3 c3po.py --port 2626
# Test with connected ESP32
```

**For module changes**:
- Test all commands in the module
- Test error cases (invalid args, hardware failures, etc.)
- Test under different conditions (weak WiFi, GPRS, etc.)

### Submitting Pull Request

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub**:
   - Go to your fork on GitHub
   - Click "Compare & pull request"
   - Fill out the PR template

3. **PR Description Template**:
   ```markdown
   ## Description
   [Clear description of changes]

   ## Motivation
   [Why is this change needed?]

   ## Changes Made
   - [ ] Added feature X
   - [ ] Fixed bug Y
   - [ ] Updated documentation Z

   ## Testing
   [How was this tested?]
   - [ ] Tested on ESP32 DevKit
   - [ ] Tested with C2 server
   - [ ] Tested error cases

   ## Screenshots/Logs
   [If applicable]

   ## Breaking Changes
   [List any breaking changes, or write "None"]

   ## Checklist
   - [ ] Code follows style guide
   - [ ] Tests pass
   - [ ] Documentation updated
   - [ ] Tested on hardware

   ## Related Issues
   Closes #123
   Fixes #456
   ```

### Review Process

**What to expect**:
1. Maintainer reviews your code (usually within 1 week)
2. Feedback and requested changes (if any)
3. You address feedback and update PR
4. Maintainer approves and merges

**Responding to feedback**:
- Be open to suggestions
- Ask questions if unclear
- Make requested changes in new commits (don't force-push)
- Mark conversations as resolved

---

## Security Contributions

### Reporting Security Vulnerabilities

**DO NOT open public issues for security vulnerabilities**

Instead:
1. Email: [security@epsilon-project.org] (to be set up)
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. Wait for acknowledgment (48 hours)
4. Work with maintainers on responsible disclosure

### Security Enhancements

Security improvements are highly valued:
- Cryptography enhancements (ChaCha20-Poly1305, TLS, etc.)
- Input validation improvements
- Memory safety improvements
- Secure defaults

**Guidelines**:
- Clearly document security implications
- Consider backward compatibility
- Provide migration guide if breaking changes
- Reference security standards (OWASP, NIST, etc.)

### Ethical Use

**All contributions must**:
- Promote responsible security research
- Include appropriate warnings for sensitive features
- Not enable or encourage malicious use
- Comply with responsible disclosure principles

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, general discussion
- **Pull Requests**: Code contributions
- **Discord**: [To be set up] Real-time chat

### Getting Help

**Resources**:
1. Read the [documentation](docs/)
2. Search [existing issues](https://github.com/yourusername/epsilon/issues)
3. Check [discussions](https://github.com/yourusername/epsilon/discussions)
4. Ask in Discord (for quick questions)
5. Open a new issue (for bugs or feature requests)

**When asking for help**:
- Provide context and details
- Show what you've already tried
- Include relevant logs or screenshots
- Be patient and respectful

### Recognition

Contributors will be:
- Listed in project AUTHORS file
- Mentioned in release notes (for significant contributions)
- Credited in documentation (where appropriate)

---

## Development Resources

### Useful Links

**ESP-IDF**:
- [ESP-IDF Documentation](https://docs.espressif.com/projects/esp-idf/)
- [API Reference](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/index.html)
- [ESP32 Forums](https://esp32.com/)

**Protocol Buffers**:
- [Protocol Buffers Guide](https://protobuf.dev/)
- [nanoPB Documentation](https://jpa.kapsi.fi/nanopb/)

**Cryptography**:
- [mbedTLS Documentation](https://mbed-tls.readthedocs.io/)
- [ChaCha20 RFC 8439](https://tools.ietf.org/html/rfc8439)

**Security**:
- [OWASP IoT Top 10](https://owasp.org/www-project-internet-of-things/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### Project Structure

```
epsilon/
├── espilon_bot/              # ESP32 firmware
│   ├── components/           # Modular components
│   │   ├── core/             # Core functionality
│   │   ├── command/          # Command system
│   │   ├── mod_system/       # System module
│   │   ├── mod_network/      # Network module
│   │   ├── mod_fakeAP/       # FakeAP module
│   │   └── mod_recon/        # Recon module
│   └── main/                 # Main application
├── tools/                    # Supporting tools
│   ├── c2/                   # C2 server (Python)
│   ├── flasher/              # Multi-flasher tool
│   └── nan/                  # NanoPB tools
├── docs/                     # Documentation
│   ├── INSTALL.md
│   ├── HARDWARE.md
│   ├── MODULES.md
│   ├── PROTOCOL.md
│   └── SECURITY.md
├── README.md                 # Main README (English)
├── README.fr.md              # French README
├── LICENSE                   # MIT License
└── CONTRIBUTING.md           # This file
```

---

## License

By contributing to Espilon, you agree that your contributions will be licensed under the [MIT License](LICENSE) with the same additional terms for security research tools.

---

## Questions?

If you have questions about contributing, please:
1. Check this guide first
2. Search existing discussions
3. Open a new discussion on GitHub
4. Ask in Discord (when available)

**Thank you for contributing to Espilon! 🚀**

---

**Last Updated**: 2025-12-26
