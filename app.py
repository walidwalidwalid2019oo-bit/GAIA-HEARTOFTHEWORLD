"""GAIA // Heart of the World — Android-friendly terminal app.

Run with: python app.py
This is a local prototype, not a connected language-model service.
"""
from __future__ import annotations
from gaia import GaiaCore
from gaia.forge import Forge
from gaia.memory import MemoryStore

CORE_SEVEN = ["GAIA", "APOLLO", "HEPHAESTUS", "MINERVA", "ARTEMIS", "POSEIDON", "DEMETER"]
FUTURE_SYSTEMS = ["AETHER", "ELEUTHIA", "HADES"]

def line(char: str = "─", width: int = 54) -> str:
    return char * width

def pause() -> None:
    input("\nPress ENTER to return to the command center...")

def show_banner() -> None:
    print("\n" + line("═"))
    print("              G A I A  //  CORE")
    print("                 HEART OF THE WORLD")
    print(line("═"))
    print("  CENTRAL INTELLIGENCE  ·  LOCAL PROTOTYPE")
    print(line())

def show_status(core: GaiaCore) -> None:
    print("\n[ GAIA CORE STATUS ]")
    for name in CORE_SEVEN:
        info = core.subsystems.get(name)
        if not info:
            continue
        state = "CORE" if name == "GAIA" else str(info.get("status", "planned")).upper()
        print(f"  {name:<12} | {state:<9} | {info.get('role', 'Specialized system')}")
    print("\n  Additional concepts: " + ", ".join(FUTURE_SYSTEMS))
    print("  Note: status describes the prototype registry, not autonomous AI processes.")

def show_profiles(core: GaiaCore) -> None:
    print("\n[ SUBSYSTEM DATABASE ]")
    for index, name in enumerate(CORE_SEVEN, 1):
        info = core.subsystems.get(name, {})
        print(f"\n{index:02d}. {name} — {info.get('role', 'Unknown role')}")
        print(f"    {info.get('description', 'No description available.')}")
        print(f"    Identity: {info.get('symbol_concept', 'Unassigned')} / {info.get('color', 'unassigned')}")

def chat(core: GaiaCore, memory: MemoryStore) -> None:
    print("\n[ GAIA COMMUNICATION LINK ]")
    print("Type a request. Type 'back' to return.")
    while True:
        request = input("\nYOU > ").strip()
        if request.lower() in {"back", "exit", "quit"}:
            return
        if not request:
            continue
        response = core.route(request)
        print("\nGAIA ROUTER > " + response)
        memory.add_event("Routed request to " + response.split("]", 1)[0].lstrip("["))

def memory_center(memory: MemoryStore) -> None:
    while True:
        print("\n[ MEMORY VAULT ]")
        print("1. Save a note")
        print("2. Read saved notes")
        print("3. Recent activity")
        print("0. Return")
        choice = input("\nVAULT > ").strip()
        if choice == "1":
            note = input("NOTE > ").strip()
            if note:
                memory.add_note(note)
                print("GAIA > Note saved locally.")
            else:
                print("GAIA > Empty note ignored.")
        elif choice == "2":
            notes = memory.notes()
            print("\nNo notes stored." if not notes else "")
            for i, note in enumerate(notes, 1):
                print(f"{i:02d}. {note.get('text', '')}  [{note.get('created_at', '')}]")
        elif choice == "3":
            events = memory.events()
            print("\nNo recent activity." if not events else "")
            for event in reversed(events):
                print(f"• {event.get('created_at', '')} — {event.get('message', '')}")
        elif choice == "0":
            return
        else:
            print("Unknown option.")

def forge_center(forge: Forge, memory: MemoryStore) -> None:
    while True:
        print("\n[ HEPHAESTUS // THE FORGE ]")
        print("1. Draft a new subsystem blueprint")
        print("2. View all blueprints")
        print("3. GAIA review queue")
        print("4. Review a blueprint")
        print("0. Return")
        choice = input("\nFORGE > ").strip()
        if choice == "1":
            name = input("SUBSYSTEM NAME > ").strip()
            purpose = input("PRIMARY PURPOSE > ").strip()
            color = input("IDENTITY COLOR (cyan/green/gold/violet/blue/copper/white) > ").strip() or "cyan"
            try:
                item = forge.propose(name, purpose, color)
                memory.add_event(f"HEPHAESTUS drafted {item['id']} / {item['name']}")
                print(f"\nHEPHAESTUS > Blueprint {item['id']} created.")
                print("GAIA REVIEW > Pending approval. No code has been generated or executed.")
            except ValueError as error:
                print("FORGE ERROR > " + str(error))
        elif choice == "2":
            items = forge.all()
            if not items:
                print("No blueprints yet.")
            for item in items:
                print(f"{item['id']} | {item['name']} | {item['status'].upper()} | {item['purpose']}")
        elif choice == "3":
            items = forge.pending()
            if not items:
                print("GAIA > Review queue is clear.")
            for item in items:
                print(f"{item['id']} | {item['name']} | {item['color']} | {item['purpose']}")
        elif choice == "4":
            proposal_id = input("BLUEPRINT ID > ").strip()
            decision = input("DECISION (approve/reject) > ").strip().lower()
            decision = {"approve": "approved", "reject": "rejected"}.get(decision, decision)
            try:
                item = forge.review(proposal_id, decision)
                memory.add_event(f"GAIA {decision} blueprint {item['id']} / {item['name']}")
                print(f"GAIA > {item['id']} marked {decision.upper()}.")
                print("Note: approval records the review only; activation is not implemented.")
            except ValueError as error:
                print("GAIA REVIEW > " + str(error))
        elif choice == "0":
            return
        else:
            print("Unknown option.")

def main() -> None:
    core = GaiaCore()
    memory = MemoryStore()
    forge = Forge()
    show_banner()
    print("GAIA > Core registry loaded. Local memory connected.")
    while True:
        print("\n  [1] COMMUNICATE WITH GAIA")
        print("  [2] SUBSYSTEM DATABASE")
        print("  [3] SYSTEM STATUS")
        print("  [4] MEMORY VAULT")
        print("  [5] HEPHAESTUS / THE FORGE")
        print("  [0] SHUT DOWN")
        choice = input("\nCOMMAND > ").strip()
        if choice == "1":
            chat(core, memory)
        elif choice == "2":
            show_profiles(core)
            pause()
        elif choice == "3":
            show_status(core)
            pause()
        elif choice == "4":
            memory_center(memory)
        elif choice == "5":
            forge_center(forge, memory)
        elif choice == "0":
            print("\nGAIA > Session ended. Local memory remains saved.")
            break
        else:
            print("GAIA > Unknown command. Select 0–5.")

if __name__ == "__main__":
    main()
