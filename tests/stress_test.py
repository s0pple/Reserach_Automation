import httpx
import asyncio
import time
import uuid
import json

# Configuration
PROXY_URL = "http://localhost:9002/v1/chat/completions"
NUM_REQUESTS = 15
MODEL = "browser-agent-gemini"

# 15 Diverse, komplexe Forschungsfragen (> 2000 Zeichen Kontext/Anforderung)
PROMPTS = [
    "Analysiere die aktuelle Marktsituation von KI-Agent-Frameworks (LangChain, AutoGPT, CrewAI). Nenne die Top 3 Player und vergleiche ihre Architektur-Ansätze in Bezug auf Skalierbarkeit und Memory-Management.",
    "Erstelle einen detaillierten Vergleich zwischen Rust und Go für die Entwicklung von High-Performance Cloud-Native Microservices. Gehe auf Speicherverwaltung, Concurrency-Modelle (Goroutines vs. Async/Await) und die Tooling-Landschaft ein.",
    "Untersuche die Auswirkungen von Quantencomputing auf die moderne Kryptographie. Erkläre Shor's Algorithmus und nenne 3 Post-Quantum-Verschlüsselungsverfahren, die aktuell vom NIST evaluiert werden.",
    "Beschreibe die Entwicklung der Transformer-Architektur von 'Attention is All You Need' bis hin zu GPT-4. Was waren die entscheidenden Durchbrüche bei Layer-Normalization und Feed-Forward-Netzwerken?",
    "Analysiere das aktuelle regulatorische Umfeld für KI in der EU (AI Act). Welche Anforderungen werden an 'High-Risk AI Systems' gestellt und wie unterscheiden sich diese von den Regelungen in den USA?",
    "Vergleiche SQL vs. NoSQL (PostgreSQL vs. MongoDB) für den Einsatz in einer global skalierten E-Commerce Plattform. Diskutiere ACID-Compliance vs. BASE-Consistency Modelle.",
    "Erkläre das 'Zero Trust Architecture' Modell im Detail. Wie lassen sich Identitätsprüfung, Mikrosegmentierung und Least-Privilege Prinzipien in einer hybriden Cloud-Infrastruktur umsetzen?",
    "Analysiere die Vor- und Nachteile von Micro-Frontends vs. Monolithische Frontends. Wann ist die Komplexität gerechtfertigt und welche Frameworks (Module Federation, Single SPA) sind führend?",
    "Untersuche die psychologischen Auswirkungen von Social Media Algorithmen auf die Aufmerksamkeitsspanne von Jugendlichen. Nenne relevante Studien und diskutiere das 'Dopamin-Loop' Modell.",
    "Beschreibe den aktuellen Stand der Kernfusions-Forschung weltweit. Was sind die Unterschiede zwischen Tokamak (ITER) und Stellarator (Wendelstein 7-X) Ansätzen?",
    "Analysiere die Strategie von Nvidia im Bereich der AI-Hardware. Warum sind H100/B200 Beschleuniger aktuell konkurrenzlos und welche Rolle spielt das CUDA-Software-Ökosystem?",
    "Erstelle eine Roadmap für die Dekarbonisierung der Schwerindustrie (Stahl, Zement). Welche Rolle spielen grüner Wasserstoff und Carbon Capture & Storage (CCS) Technologien?",
    "Vergleiche die Wirtschaftssysteme von Japan (Abenomics) und Deutschland im Hinblick auf den demografischen Wandel. Welche Lösungsansätze gibt es gegen den Fachkräftemangel?",
    "Untersuche die Geschichte und den Einfluss der Bauhaus-Schule auf das moderne Webdesign. Wie lassen sich Prinzipien wie 'Form follows Function' in Current-UI-Trends (Bento Grid, Glassmorphism) wiederfinden?",
    "Analysiere die Sicherheit von Smart Contracts auf der Ethereum Blockchain. Nenne die Top 3 Schwachstellen (Reentrancy, Integer Overflow, Front-running) und Best Practices für Audits."
]

async def send_request(client, i, prompt):
    request_id = f"stress-test-{uuid.uuid4().hex[:8]}"
    print(f"[{i+1}/{NUM_REQUESTS}] Sending Request (ID: {request_id})...")
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Du bist ein Senior Research Assistant. Antworte immer strukturiert in Markdown mit Quellenhinweisen."},
            {"role": "user", "content": prompt}
        ],
        "request_id": request_id  # Custom ID propagation
    }
    
    start_time = time.time()
    try:
        # Long timeout for Browser Agent
        response = await client.post(PROXY_URL, json=payload, timeout=600.0)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            print(f"[{i+1}/{NUM_REQUESTS}] SUCCESS in {duration:.2f}s | Length: {len(content)}")
            return True
        else:
            print(f"[{i+1}/{NUM_REQUESTS}] FAILED with Status {response.status_code} | {response.text}")
            return False
    except Exception as e:
        print(f"[{i+1}/{NUM_REQUESTS}] ERROR: {str(e)}")
        return False

async def main():
    print("============================================================")
    print(f"🚀 STARTING ULTIMATE STRESS TEST: {NUM_REQUESTS} REQUESTS (PARALLEL QUEUE FILL)")
    print("============================================================")
    
    async with httpx.AsyncClient() as client:
        # We send all requests in parallel to fill the proxy/task queue
        tasks = [send_request(client, i, PROMPTS[i]) for i in range(NUM_REQUESTS)]
        results = await asyncio.gather(*tasks)
            
    success_count = sum(1 for r in results if r)
    print("============================================================")
    print(f"🏁 STRESS TEST FINISHED")
    print(f"Total Requests: {NUM_REQUESTS}")
    print(f"Success Rating: {success_count}/{NUM_REQUESTS} ({(success_count/NUM_REQUESTS)*100:.1f}%)")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
