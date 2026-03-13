import asyncio
import sys
import os
import unittest
from unittest.mock import patch, AsyncMock

# Ensure the root directory is in sys.path so 'src' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.dummy_tools import register_dummy_tools
from src.agents.local_router.router import analyze_intent

class TestLocalRouter(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Register dummy tools so they are available in the registry for tests
        register_dummy_tools()

    @patch("src.agents.local_router.router.AsyncClient")
    async def test_1_einfaches_tool(self, mock_client_class):
        # Mock the Ollama response for Test 1
        mock_instance = mock_client_class.return_value
        mock_instance.chat = AsyncMock(return_value={
            "message": {
                "content": '{"tool": "cv_click", "parameters": {"target": "Warenkorb"}}'
            }
        })
        
        print("\n[Test 1] Eingabe: 'Klicke auf den Warenkorb'")
        intent = await analyze_intent("Klicke auf den Warenkorb")
        print(f"  -> Router Entscheidung: {intent}")
        
        self.assertEqual(intent.get("tool"), "cv_click")
        self.assertEqual(intent.get("parameters", {}).get("target"), "Warenkorb")

    @patch("src.agents.local_router.router.AsyncClient")
    async def test_2_komplexes_tool_mit_parameter(self, mock_client_class):
        # Mock the Ollama response for Test 2
        mock_instance = mock_client_class.return_value
        mock_instance.chat = AsyncMock(return_value={
            "message": {
                "content": '{"tool": "venture_analysis", "parameters": {"domain": "vertikale Landwirtschaft"}}'
            }
        })
        
        print("\n[Test 2] Eingabe: 'Analysiere den Markt für vertikale Landwirtschaft'")
        intent = await analyze_intent("Analysiere den Markt für vertikale Landwirtschaft")
        print(f"  -> Router Entscheidung: {intent}")
        
        self.assertEqual(intent.get("tool"), "venture_analysis")
        self.assertEqual(intent.get("parameters", {}).get("domain"), "vertikale Landwirtschaft")

    @patch("src.agents.local_router.router.AsyncClient")
    async def test_3_resilienz_offline(self, mock_client_class):
        # Mock an exception to simulate Ollama being offline
        mock_instance = mock_client_class.return_value
        mock_instance.chat = AsyncMock(side_effect=Exception("Connection refused"))
        
        print("\n[Test 3] Resilienz: Ollama-Service ist offline.")
        intent = await analyze_intent("Klicke auf den Warenkorb")
        print(f"  -> Fallback Output: {intent}")
        
        self.assertEqual(intent.get("tool"), "error")
        self.assertEqual(intent.get("message"), "Lokaler Router nicht erreichbar.")

if __name__ == "__main__":
    unittest.main()

