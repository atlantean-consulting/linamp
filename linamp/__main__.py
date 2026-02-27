import sys


def main():
    if "--library" in sys.argv:
        from linamp.library import LibraryApp
        LibraryApp().run()
    else:
        from linamp.app import LinampApp
        LinampApp().run()


if __name__ == "__main__":
    main()
