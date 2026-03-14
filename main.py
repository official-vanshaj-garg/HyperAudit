from src.config import DATA_DIR, OUTPUTS_DIR, CACHE_DIR


def main() -> None:
    print("HyperAudit project initialized.")
    print(f"Data dir: {DATA_DIR}")
    print(f"Outputs dir: {OUTPUTS_DIR}")
    print(f"Cache dir: {CACHE_DIR}")


if __name__ == "__main__":
    main()