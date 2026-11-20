# Aspire -> SCM Post Processor
---
## About

This module helps convert a plain .XXL G Code file into an .XXL and .PGM file that works with legacy SCM CNC using Xilog for its controller.

It is based on output from Aspire 12.5. 

## Instructions

1. Create a virtual environment and install the requirements from the Pipfile
2. Update settings.py with your preferences
3. run python process.py
4. Select a G Code .XXL file to convert

## WARNING

**This script runs for a very specific machine and workflow. Results are not garunteed. Safe operation of your CNC is not garunteed. Basically, don't even use this, it is just for me and it's a code sample I want to keep around.**
