import subprocess
import sys
import os
import struct
from pathlib import Path

VENDOR_DIR = Path(__file__).parent
LIBPG_DIR = VENDOR_DIR / "libpg_query"
BRANCH = "17-latest"
REPO = "https://github.com/pganalyze/libpg_query.git"


def get_arch():
    """Defines the Python architecture."""
    if sys.platform == "win32":
        return "x64" if struct.calcsize("P") == 8 else "x86"
    else:
        return (
            "arm64"
            if struct.calcsize("P") == 8 and sys.platform == "darwin"
            else "x86_64"
        )


def get_machine():
    """Returns MACHINE for link.exe."""
    arch = get_arch()
    if arch == "x64":
        return "X64"
    elif arch == "x86":
        return "X86"
    elif arch == "arm64":
        return "ARM64"
    else:
        return "X64"


def setup_env():
    """Configures the build environment."""
    if sys.platform == "win32":
        arch = get_arch()
        vs_path = None
        vswhere = Path(
            "C:/Program Files (x86)/Microsoft Visual "
            "Studio/Installer/vswhere.exe",
        )

        if vswhere.exists():
            result = subprocess.run(  # noqa: S603
                [str(vswhere), "-latest", "-property", "installationPath"],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                vs_path = Path(result.stdout.strip())

        if not vs_path:
            for year in ["2022", "2019", "2017"]:
                for edition in ["Community", "Professional", "Enterprise"]:
                    p = Path(
                        "C:/Program Files/Microsoft Visual Studio/"
                        f"{year}/{edition}",
                    )
                    if p.exists():
                        vs_path = p
                        break
                if vs_path:
                    break

        if not vs_path:
            print("ERROR: Visual Studio not found")
            return False

        # MSVC paths
        vc_path = vs_path / "VC" / "Tools" / "MSVC"
        if vc_path.exists():
            versions = sorted(os.listdir(vc_path), reverse=True)
            if versions:
                msvc_ver = versions[0]
                bin_path = vc_path / msvc_ver / "bin" / f"Host{arch}" / arch
                include_path = vc_path / msvc_ver / "include"
                lib_path = vc_path / msvc_ver / "lib" / arch

                if bin_path.exists():
                    os.environ["PATH"] = (
                        str(bin_path) + os.pathsep + os.environ["PATH"]
                    )
                if include_path.exists():
                    os.environ["INCLUDE"] = (
                        str(include_path)
                        + os.pathsep
                        + os.environ.get("INCLUDE", "")
                    )
                if lib_path.exists():
                    os.environ["LIB"] = (
                        str(lib_path) + os.pathsep + os.environ.get("LIB", "")
                    )

        # Windows SDK paths
        kit_path = Path("C:/Program Files (x86)/Windows Kits/10")
        if kit_path.exists():
            include_base = kit_path / "Include"
            lib_base = kit_path / "Lib"

            if include_base.exists():
                versions = sorted(os.listdir(str(include_base)), reverse=True)
                if versions:
                    sdk_ver = versions[0]
                    sdk_include = include_base / sdk_ver
                    os.environ["INCLUDE"] = (
                        str(sdk_include / "ucrt")
                        + os.pathsep
                        + str(sdk_include / "um")
                        + os.pathsep
                        + str(sdk_include / "shared")
                        + os.pathsep
                        + os.environ.get("INCLUDE", "")
                    )

            if lib_base.exists():
                versions = sorted(os.listdir(str(lib_base)), reverse=True)
                if versions:
                    sdk_ver = versions[0]
                    sdk_lib = lib_base / sdk_ver
                    os.environ["LIB"] = (
                        str(sdk_lib / "um" / arch)
                        + os.pathsep
                        + str(sdk_lib / "ucrt" / arch)
                        + os.pathsep
                        + os.environ.get("LIB", "")
                    )

        return True
    return True


def clone():
    """Clones the repository if it hasn't been cloned yet."""
    if not LIBPG_DIR.exists():
        subprocess.check_call(  # noqa: S603
            ["git", "clone", "-b", BRANCH, REPO, str(LIBPG_DIR)]  # noqa: S607
        )
    else:
        subprocess.check_call(["git", "fetch", "--tags"], cwd=LIBPG_DIR)  # noqa: S607
        subprocess.check_call(["git", "checkout", BRANCH], cwd=LIBPG_DIR)  # noqa: S607, S603
        subprocess.check_call(["git", "pull", "origin", BRANCH], cwd=LIBPG_DIR)  # noqa: S607, S603


def build():
    """Building the library."""
    if sys.platform == "win32":
        if not setup_env():
            print(
                "ERROR: Cannot find Visual Studio. Install Visual Studio "
                "2022 with C++ tools.",
            )
            print("Download: https://visualstudio.microsoft.com/ru/downloads/")
            sys.exit(1)

        subprocess.check_call(  # noqa: S602
            ["nmake", "/F", "Makefile.msvc", "clean"],  # noqa: S607
            cwd=LIBPG_DIR, shell=True,
        )
        subprocess.check_call(  # noqa: S602
            ["nmake", "/F", "Makefile.msvc", "all"],  # noqa: S607
            cwd=LIBPG_DIR, shell=True,
        )
    else:
        subprocess.check_call(["make", "clean"], cwd=LIBPG_DIR)  # noqa: S607
        subprocess.check_call(["make"], cwd=LIBPG_DIR)  # noqa: S607


def link():
    """Links a dynamic library."""
    if sys.platform == "win32":
        obj_files = list(LIBPG_DIR.glob("*.obj"))
        exclude_test = [
            "deparse", "fingerprint", "fingerprint_opts",
            "is_utility_stmt", "normalize", "normalize_error",
            "parse", "parse_opts", "parse_plpgsql",
            "parse_protobuf", "parse_protobuf_opts",
            "simple", "simple_error", "simple_plpgsql",
            "split", "summary", "summary_truncate", "main",
        ]
        obj_files = [
            f for f in obj_files if not any(e == f.stem for e in exclude_test)
        ]

        if not obj_files:
            raise RuntimeError("No object files found. Build failed?")

        lib_name = "libpg_query.dll"
        machine = get_machine()
        def_file = LIBPG_DIR / "pg_query.def"
        def_file.write_text(
            "EXPORTS\npg_query_parse\npg_query_free_parse_result\n"
        )

        subprocess.check_call(  # noqa: S602
            ["link", "/DLL", f"/MACHINE:{machine}", f"/OUT:{lib_name}"]
            + [str(f) for f in obj_files]
            + [f"/DEF:{def_file}"],
            cwd=LIBPG_DIR, shell=True,
        )

        return LIBPG_DIR / lib_name

    else:
        # Linux/macOS: ищем ВСЕ .o файлы рекурсивно, исключая тесты
        obj_files = []
        for f in LIBPG_DIR.rglob("*.o"):
            # Пропускаем файлы из examples/ и test/ директорий
            if "examples" in f.parts or "test" in f.parts:
                continue
            # Пропускаем файлы с main (тесты)
            if f.stem in ("main", "deparse", "fingerprint", "fingerprint_opts",
                         "is_utility_stmt", "normalize", "normalize_error",
                         "parse", "parse_opts", "parse_plpgsql",
                         "parse_protobuf", "parse_protobuf_opts",
                         "simple", "simple_error", "simple_plpgsql",
                         "split", "summary", "summary_truncate"):
                continue
            obj_files.append(f)

        if not obj_files:
            raise RuntimeError("No object files found. Build failed?")

        # Создаём статическую библиотеку
        static_lib = LIBPG_DIR / "libpg_query.a"
        subprocess.check_call(  # noqa: S603
            ["ar", "rcs", str(static_lib)] + [str(f) for f in obj_files],
            cwd=LIBPG_DIR,
        )

        # Линкуем динамическую библиотеку из статической
        if sys.platform == "darwin":
            lib_name = "libpg_query.dylib"
            arch = get_arch()
            subprocess.check_call(  # noqa: S603
                ["gcc", "-arch", arch, "-dynamiclib",  # noqa: S607
                 "-o", lib_name, str(static_lib)],
                cwd=LIBPG_DIR,
            )
        else:
            lib_name = "libpg_query.so"
            # -Wl,--whole-archive заставляет линковщика включить все символы
            subprocess.check_call(  # noqa: S603
                ["gcc", "-shared", "-fPIC",  # noqa: S607
                 "-Wl,--whole-archive", str(static_lib),
                 "-Wl,--no-whole-archive",
                 "-o", lib_name],
                cwd=LIBPG_DIR,
            )

        return LIBPG_DIR / lib_name


def copy_to_core(lib_path):
    """Copies the compiled library to the core directory."""
    import shutil

    core_dir = (
        Path(__file__).parent.parent / "src" / "postgres_csvpatcher" / "core"
    )
    core_dir.mkdir(parents=True, exist_ok=True)
    dest = core_dir / lib_path.name
    shutil.copy2(lib_path, dest)
    return dest


def main():
    clone()
    build()
    lib_path = link()
    dest = copy_to_core(lib_path)
    print(f"Library built and copied to {dest}")


if __name__ == "__main__":
    main()
