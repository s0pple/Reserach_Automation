#!/usr/bin/env python3
"""
PHASE 4: Test the new submission logic
This script verifies that the robust 3-tier fallback strategy works
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_submission_strategies():
    """Test all three submission strategies on a real AI Studio page"""
    print("=" * 70)
    print("PHASE 4: TESTING ROBUST SUBMISSION LOGIC")
    print("=" * 70)
    
    async with async_playwright() as p:
        print("\n[1] Launching browser...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.create_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        try:
            print("[2] Navigating to Google AI Studio...")
            await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            
            # Dismiss banners
            print("[3] Dismissing banners...")
            try:
                await page.get_by_text("Agree").first.click(timeout=1500)
                await page.wait_for_timeout(1000)
            except:
                pass
            
            # Fill the prompt
            print("[4] Filling prompt box...")
            prompt_box = page.locator("textarea").last
            test_prompt = "Explain quantum computing in one sentence."
            await prompt_box.click()
            await prompt_box.clear()
            await prompt_box.fill(test_prompt)
            await page.wait_for_timeout(500)
            
            # Count turns BEFORE
            turn_count_before = await page.locator(".model-turn").count()
            print(f"    Turn count BEFORE submission: {turn_count_before}")
            
            submitted = False
            
            # STRATEGY 1: Text match
            print("\n[STRATEGY 1] Trying: get_by_text('Run', exact=True).last.click()...")
            try:
                run_button = page.get_by_text("Run", exact=True).last
                count = await run_button.count()
                print(f"    Found {count} 'Run' button(s)")
                if count > 0:
                    await run_button.click(timeout=3000)
                    print("    ✅ STRATEGY 1 SUCCESS: Clicked Run button via text match!")
                    submitted = True
            except Exception as e1:
                print(f"    ❌ STRATEGY 1 FAILED: {e1}")
            
            # STRATEGY 2: aria-label / title
            if not submitted:
                print("\n[STRATEGY 2] Trying: button[aria-label*='run' i], button[title*='run' i]...")
                try:
                    run_button = page.locator("button[aria-label*='run' i], button[title*='run' i]").last
                    count = await run_button.count()
                    print(f"    Found {count} run button(s) via selectors")
                    if count > 0:
                        await run_button.click(timeout=3000)
                        print("    ✅ STRATEGY 2 SUCCESS: Clicked Run button via aria-label/title!")
                        submitted = True
                except Exception as e2:
                    print(f"    ❌ STRATEGY 2 FAILED: {e2}")
            
            # STRATEGY 3: Keyboard with focus
            if not submitted:
                print("\n[STRATEGY 3] Trying: Focus textarea + Control+Enter...")
                try:
                    await prompt_box.focus()
                    await page.wait_for_timeout(200)
                    await page.keyboard.press("Control+Enter")
                    print("    ✅ STRATEGY 3: Sent Control+Enter with focus!")
                    submitted = True
                except Exception as e3:
                    print(f"    ❌ STRATEGY 3 FAILED: {e3}")
            
            if submitted:
                print("\n" + "=" * 70)
                print("✅ SUBMISSION SUCCESSFUL")
                print("=" * 70)
                
                # Wait for response
                print("\n[5] Waiting for AI Studio response (15 seconds)...")
                await page.wait_for_timeout(15000)
                
                # Check for new turns
                turn_count_after = await page.locator(".model-turn").count()
                print(f"    Turn count AFTER: {turn_count_after}")
                
                if turn_count_after > turn_count_before:
                    print(f"\n✅ SUCCESS: Got {turn_count_after - turn_count_before} new response(s)!")
                    
                    # Extract text
                    model_turns = await page.locator(".model-turn").all()
                    response_text = await model_turns[-1].inner_text()
                    print(f"\n[RESPONSE PREVIEW]:\n{response_text[:500]}...")
                else:
                    print("\n⚠️  WARNING: No new response detected after submission")
                    print("    Possible reasons:")
                    print("    1. Submission may have failed silently")
                    print("    2. Response is still generating")
                    print("    3. Locator selector is incorrect")
            else:
                print("\n" + "=" * 70)
                print("❌ ALL SUBMISSION STRATEGIES FAILED")
                print("=" * 70)
                print("\nNeed to investigate further:")
                print("- Check browser HTML structure")
                print("- Verify Run button selectors")
                print("- Check if keyboard events are being captured")
            
            # Take screenshot for debugging
            print("\n[6] Taking screenshot for debugging...")
            await page.screenshot(path="temp/test_submission_result.png")
            print("    Saved to: temp/test_submission_result.png")
            
        finally:
            await browser.close()
            print("\n[7] Browser closed.")


if __name__ == "__main__":
    asyncio.run(test_submission_strategies())
