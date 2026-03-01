# 🤝 Contributing to Nagomi Clinical Forensic

**Welcome!** We're thrilled you're interested in contributing to the Nagomi Clinical Forensic. This project aims to democratize access to medical research through AI-powered analysis.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Development Guidelines](#development-guidelines)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Community](#community)

## 🤟 Code of Conduct

This project follows a code of respect and inclusion. We welcome contributions from everyone, regardless of background or experience level. Please be kind, constructive, and professional in all interactions.

## 🚀 Getting Started

### Prerequisites
- **Node.js 18+** ([download](https://nodejs.org))
- **Python 3.8+** ([download](https://python.org))
- **Git** ([download](https://git-scm.com))
- **Gemini CLI** ([install guide](https://gcli.dev))

### Quick Setup
```bash
# Fork and clone the repository
git clone https://github.com/avivlyweb/pubmed-gemini-extension.git
cd pubmed-gemini-extension

# Install dependencies
npm install

# Build the extension
npm run build

# Link for development testing
gemini extensions link pubmed-gemini/
```

## 🛠️ Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/avivlyweb/pubmed-gemini-extension.git
cd pubmed-gemini-extension
```

### 2. Install Dependencies
```bash
# Node.js dependencies
npm install

# Python dependencies (for MCP server)
pip3 install httpx rich mcp
```

### 3. Build and Test
```bash
# Build the extension
npm run build

# Link for development
gemini extensions link pubmed-gemini/

# Test in Gemini CLI
gemini
/nagomi:search "test query"
```

## 💡 How to Contribute

### Types of Contributions

#### 🐛 Bug Reports
- Use [GitHub Issues](https://github.com/avivlyweb/pubmed-gemini-extension/issues)
- Include detailed steps to reproduce
- Specify your environment (OS, Node.js/Python versions)
- Add screenshots if relevant

#### 💡 Feature Requests
- Check existing issues first
- Clearly describe the proposed feature
- Explain the use case and benefits
- Consider implementation complexity

#### 📝 Documentation
- Fix typos or unclear explanations
- Add examples or tutorials
- Translate documentation
- Create video tutorials

#### 🔧 Code Contributions
- Fix bugs or implement features
- Improve performance or reliability
- Add tests or refactor code
- Update dependencies

### Finding Issues to Work On

1. **Good First Issues**: Look for issues labeled `good first issue`
2. **Bug Fixes**: Check for `bug` labeled issues
3. **Feature Requests**: Look for `enhancement` labeled issues
4. **Documentation**: Check for `documentation` labeled issues

## 📏 Development Guidelines

### Code Style

#### TypeScript/JavaScript
- Use TypeScript for type safety
- Follow ESLint configuration
- Use meaningful variable names
- Add JSDoc comments for functions

#### Python
- Follow PEP 8 style guide
- Use type hints
- Add docstrings for functions
- Keep functions focused and testable

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add PICO analysis to search results
fix: resolve memory leak in MCP server
docs: update installation instructions
test: add unit tests for quality assessment
```

### Branch Naming

```
feature/add-pico-analysis
bugfix/memory-leak-fix
docs/update-readme
test/add-unit-tests
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
npm test

# Run specific test file
npm test -- --grep "quality assessment"

# Run Python tests
cd pubmed-mcp
python -m pytest tests/
```

### Testing Your Changes

#### Manual Testing
```bash
# Link your development version
gemini extensions link pubmed-gemini/

# Test in Gemini CLI
gemini
/nagomi:search "exercise for back pain"
/nagomi:analyze "34580864"
/nagomi:synthesis "telemedicine"
```

#### Automated Testing
```bash
# Run the test script
./TEST_MEDICAL_RESEARCH.sh
```

## 📤 Submitting Changes

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
- Write clear, focused commits
- Test your changes thoroughly
- Update documentation if needed

### 3. Test Your Changes
```bash
# Run tests
npm test

# Manual testing
gemini extensions link pubmed-gemini/
# Test functionality
```

### 4. Submit a Pull Request

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Screenshots/videos if UI changes
   - Links to related issues

3. **Address Review Comments**:
   - Be responsive to feedback
   - Make requested changes
   - Keep conversations professional

### Pull Request Checklist
- [ ] Tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Changes tested manually
- [ ] No breaking changes without discussion

## 🌍 Community

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Request Comments**: Code review discussions

### Recognition
Contributors are recognized in:
- GitHub repository contributors list
- Release notes for significant contributions
- Special mentions in documentation

### Getting Help
- Check existing issues and documentation first
- Be specific about your problem or question
- Include relevant context (OS, versions, error messages)
- Share code snippets when relevant

## 🎯 Areas for Contribution

### High Priority
- **Performance Optimization**: Speed up search and analysis
- **Error Handling**: Better error messages and recovery
- **Documentation**: User guides and API documentation
- **Testing**: More comprehensive test coverage

### Medium Priority
- **New Features**: Additional medical research tools
- **UI/UX**: Better command interfaces
- **Internationalization**: Support for multiple languages
- **Accessibility**: Screen reader support

### Future Ideas
- **Mobile Support**: iOS/Android companion apps
- **Integration**: Connect with other research databases
- **Visualization**: Charts and graphs for results
- **Collaboration**: Multi-user research sessions

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the same MIT License that covers the project.

## 🙏 Acknowledgments

Thank you for contributing to open-source medical research tools! Your work helps make scientific knowledge more accessible to everyone.

**Questions?** Don't hesitate to ask in GitHub Issues or Discussions! 🚀
