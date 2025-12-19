from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv, Environment
from conan.tools.microsoft import unix_path
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain"
    test_type = "explicit"
    win_bash = True

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        vbe = VirtualBuildEnv(self)
        vbe.generate()
        if not cross_building(self):
            vre = VirtualRunEnv(self)
            vre.generate(scope="build")
        env = Environment()
        # Tell Python to assume UTF-8 encoding to work around character encoding issues while building Qt WebEngine on Polish locale on Windows.
        env.define("PYTHONUTF8", "1")
        # TODO: to remove when properly handled by conan (see https://github.com/conan-io/conan/issues/11962)
        env.unset("VCPKG_ROOT")
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("conanbuildenv_pkg_config_path")
        if self.settings_build.os == "Macos":
            # On macOS, SIP resets DYLD_LIBRARY_PATH injected by VirtualBuildEnv & VirtualRunEnv
            dyld_library_path = "$DYLD_LIBRARY_PATH"
            dyld_library_path_build = vbe.vars().get("DYLD_LIBRARY_PATH")
            if dyld_library_path_build:
                dyld_library_path = f"{dyld_library_path_build}:{dyld_library_path}"
            if not cross_building(self):
                dyld_library_path_host = vre.vars().get("DYLD_LIBRARY_PATH")
                if dyld_library_path_host:
                    dyld_library_path = f"{dyld_library_path_host}:{dyld_library_path}"
            save(self, "bash_env", f'export DYLD_LIBRARY_PATH="{dyld_library_path}"')
            env.define_path("BASH_ENV", os.path.abspath("bash_env"))
        
    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)
        if self._settings_build.os == "Windows":
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/cci.latest")

    def requirements(self):
        self.requires("libiconv/1.17")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _mc_parser_source(self):
        return os.path.join(self.source_folder, "mc_parser.yy")

    def test(self):
        self.run("bison --version")
        self.run("yacc --version")
        self.run(f"bison -d {unix_path(self, self._mc_parser_source)}")
