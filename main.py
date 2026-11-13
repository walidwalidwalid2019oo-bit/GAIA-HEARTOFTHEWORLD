"""Entry point for the GAIA terminal prototype."""

from gaia import GaiaCore


def main() -> None:
    gaia = GaiaCore()
    print("=" * 48)
    print("             GAIA // HEART OF THE WORLD")
    print("=" * 48)
    print("Central coordinator initialized.")
    print("Commands: status | help | exit")
    print("")

    while True:
        try:
            request = input("YOU > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGAIA > Session closed.")
            break

        if not request:
            continue

        command = request.lower()
        if command in {"exit", "quit", "shutdown"}:
            print("GAIA > Session closed.")
            break
        if command == "status":
            print(gaia.status_report())
            continue
        if command == "help":
            print("Ask a question or describe a task. Try: explain photosynthesis")
            print("Use 'status' to view the subsystem registry.")
            continue

        print(gaia.route(request))
        print("")


if __name__ == "__main__":
    main()
