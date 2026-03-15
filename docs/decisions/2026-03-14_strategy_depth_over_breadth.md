# Strategy Record: Depth Over Breadth (The Research Weapon vs. Generalist Bots)

**Date:** March 14, 2026

## Context
A strategic discussion evaluated whether our system (Clawdbot / Venture Analyst) should pivot towards becoming a general-purpose AI assistant (like OpenClaw/Moltbot), focusing on breadth (e.g., managing calendars, buying groceries, creating repositories).

## Decision
**We explicitly reject the generalist approach.** We are not building a second OpenClaw. Our strategic advantage is a radical focus on **Depth instead of Breadth**. 

A generalist bot is a commodity that commercial tools will soon offer out-of-the-box. Our system's unique moat ("Hebel") is its ability to use brute force against anti-bot blockades (via our "Sight & Touch" Hybrid Architecture), extract massive datasets, and run them through highly specialized, critical agents (The Crucible). 

**We are building a Research Weapon, not a daily chore automator.**

## Core Principles & Roadmap
To execute this strategy, we focus on the absolute minimum required for maximum impact:

1. **Total Visibility (The Watchtower):** 
   Before the machine surfs completely autonomously, we must have live visibility via Telegram into what is happening inside the God-Container. Without visual control, complex scraping attempts are flying blind. *(Note: The baseline for this was established in Phase 1 with the `/watch` command).*

2. **Extreme Compression (Smart Synthesis):** 
   A 50,000-character Qwen/Gemini report is unreadable on a smartphone. For the user on the go (e.g., on a train), we need immediately actionable facts. We will insert a powerful LLM (e.g., Gemini 1.5 Pro) as a final filter to compress massive reports into exactly **one page of an Executive Summary**. The raw data remains securely on the server.

3. **No Everyday Chores:** 
   We will intentionally skip automating everyday tasks. Every feature must serve the goal of deep, autonomous market and venture research.
