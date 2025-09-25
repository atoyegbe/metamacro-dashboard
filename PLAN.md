# Windsurf + Claude 4 Agent Prompts: Streamlit to TUI Conversion

## 1. Project Analysis Prompt
```
I have a Streamlit project called MetaMacro - a market analysis platform for sector momentum, portfolio analysis, and market regime detection. 

Analyze the entire codebase and:
- Map all Streamlit components to Textual equivalents
- Identify data flow patterns and state management
- List all dependencies that need TUI alternatives
- Create a conversion strategy with file structure

Provide a complete migration plan with specific file changes needed.
```

## 2. Architecture Implementation Prompt
```
Create a complete TUI version of my MetaMacro Streamlit app using Python Textual.

Requirements:
- Convert ALL existing functionality to terminal interface
- Use Textual for UI framework, Rich for styling, plotext for charts
- Maintain the same user experience and data analysis capabilities
- Create proper file structure with main.py, components/, and styles/
- Include keyboard shortcuts and navigation
- Handle real-time data updates

Generate complete working code, don't just show examples.
```

## 3. Component-by-Component Migration Prompt
```
I'm migrating from Streamlit to TUI. Here's my current Streamlit code:

[PASTE YOUR STREAMLIT CODE HERE]

Convert this EXACTLY to Textual TUI:
- Replace every st.widget with appropriate Textual widget
- Convert all charts to plotext terminal charts
- Maintain all interactive functionality
- Preserve data processing logic
- Add proper event handling
- Include error handling and loading states

Provide complete, runnable code with all imports.
```

## 4. Data Visualization Conversion Prompt
```
Convert all my Streamlit charts and data displays to terminal-compatible versions:

[PASTE YOUR PLOTTING/CHART CODE HERE]

Transform to:
- plotext for line/bar/scatter plots in terminal
- Rich tables with proper formatting for data
- ASCII indicators for market regimes
- Color-coded terminal output for sector momentum
- Progress bars and metrics displays

Make it visually appealing in terminal while preserving all data insights.
```

## 5. Full Application Assembly Prompt
```
Combine all converted components into a complete MetaMacro TUI application.

Create:
1. main.py - Entry point with Textual App class
2. views/ - All dashboard and analysis screens
3. components/ - Reusable UI widgets
4. utils/ - Data processing utilities (unchanged from Streamlit)
5. styles.css - Terminal styling
6. requirements.txt - Updated dependencies

The app should:
- Launch and work immediately after pip install
- Have identical functionality to original Streamlit version
- Include help system and keyboard shortcuts
- Handle errors gracefully
- Support terminal resizing

Generate ALL files needed for a working application.
```

## 6. Testing & Deployment Prompt
```
Finalize the MetaMacro TUI application:

1. Add comprehensive error handling and user feedback
2. Create setup.py for easy installation
3. Add CLI arguments for different analysis modes
4. Include data export functionality
5. Add keyboard shortcuts documentation
6. Create README with installation and usage instructions
7. Test terminal compatibility across different sizes

Ensure production-ready code that works on any terminal.
```

## Key Instructions for Windsurf:

**Always include in your prompts:**
- "Generate complete, runnable code"
- "Don't show examples, create the actual implementation"
- "Include all necessary imports and dependencies"
- "Create proper file structure with all files"

**For best results:**
1. Run prompts sequentially
2. Test each component before moving to next
3. Paste your actual Streamlit code in prompts 3-4
4. Let Claude 4 agent see the full project structure

**Windsurf-specific request:**
```
Please create all files in the workspace and ensure the TUI application runs with: 
python main.py

Test that all functionality works exactly like the original Streamlit version.
``