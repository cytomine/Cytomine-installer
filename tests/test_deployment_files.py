import os
import yaml
from tempfile import TemporaryDirectory
from unittest import TestCase

from cytomine_installer.deployment.env_store import UnknownValueTypeError
from cytomine_installer.deployment.deployment_files import (
    DockerComposeFile,
    ConfigFile,
    EditableDockerCompose,
    UnknownConfigSection,
)
from tests.util import UUID_PATTERN


class TestDockerComposeFile(TestCase):
    def testValidFile(self):
        tests_path = os.path.dirname(__file__)
        dc_path = os.path.join(tests_path, "files")
        dc_filename = "docker_compose.valid.yml"
        docker_compose_file = DockerComposeFile(dc_path, filename=dc_filename)
        services = {
            "nginx",
            "core",
            "postgresql",
            "mongodb",
            "rabbitmq",
            "memcached",
            "pims",
        }
        self.assertSetEqual(services, set(docker_compose_file.services))
        self.assertIsNone(docker_compose_file.version)


class TestConfigFile(TestCase):
    def testMinimalFile(self):
        tests_path = os.path.dirname(__file__)
        ce_path = os.path.join(tests_path, "files")
        ce_filename = "cytomine.mini.yml"
        config_file = ConfigFile(ce_path, filename=ce_filename)
        self.assertEqual(config_file.path, ce_path)
        self.assertEqual(config_file.filename, ce_filename)
        self.assertEqual(
            config_file.filepath, os.path.join(ce_path, ce_filename)
        )
        self.assertEqual(
            config_file.global_envs.get_env("namespace1", "VAR1"), "value1"
        )
        self.assertEqual(
            config_file.global_envs.get_env("namespace1", "VAR2"), "value2"
        )
        self.assertRegex(
            config_file.global_envs.get_env("namespace2", "KEY1"), UUID_PATTERN
        )
        self.assertRegex(
            config_file.global_envs.get_env("namespace2", "KEY2"), UUID_PATTERN
        )

        self.assertEqual(len(config_file.servers), 1)
        self.assertEqual(config_file.servers[0], "default")
        default_store = config_file.server_store("default")
        self.assertEqual(default_store.get_env("core", "EMAIL"), "emailcore")
        self.assertEqual(
            default_store.get_env("core", "VAR1"),
            config_file.global_envs.get_env("namespace1", "VAR1"),
        )
        self.assertRegex(default_store.get_env("core", "GENERATED"), UUID_PATTERN)
        self.assertEqual(
            default_store.get_env("rabbitmq", "VAR1"),
            config_file.global_envs.get_env("namespace1", "VAR1"),
        )
        self.assertEqual(
            default_store.get_env("rabbitmq", "VAR2"),
            config_file.global_envs.get_env("namespace2", "KEY1"),
        )

    def testFileWithInvalidValueType(self):
        tests_path = os.path.dirname(__file__)
        ce_path = os.path.join(tests_path, "files")
        ce_filename = "cytomine.unknown-value-type.yml"
        with self.assertRaises(UnknownValueTypeError):
            ConfigFile(ce_path, filename=ce_filename)

    def testFileWithInvalidTopLevelSection(self):
        tests_path = os.path.dirname(__file__)
        ce_path = os.path.join(tests_path, "files")
        ce_filename = "cytomine.invalid-top-level-sections.yml"
        with self.assertRaises(UnknownConfigSection):
            ConfigFile(ce_path, filename=ce_filename)

    def testMerge(self):
        tests_path = os.path.dirname(__file__)
        ce_path = os.path.join(tests_path, "files")
        ce_filename1 = "cytomine.mini.2.yml"
        ce_filename2 = "cytomine.mini.3.yml"
        ce_filename3 = "cytomine.mini.merge2->3.yml"
        config_file1 = ConfigFile(ce_path, filename=ce_filename1)
        config_file2 = ConfigFile(ce_path, filename=ce_filename2)
        merge_config_file = ConfigFile(ce_path, filename=ce_filename3)
        config_file3 = ConfigFile.merge(config_file1, config_file2)

        export3 = config_file3.export_dict()
        self.assertDictEqual(export3, merge_config_file.export_dict())


class TestEditableDockerCompose(TestCase):
    def testEmpty(self):
        edc = EditableDockerCompose()

        with TemporaryDirectory() as tmpdir:
            edc.write_to(tmpdir)
            with open(
                os.path.join(tmpdir, "docker-compose.yml"), "r", encoding="utf8"
            ) as file:
                edc_content = yaml.load(file, Loader=yaml.Loader)

        self.assertDictEqual({"services": {}}, edc_content)

    def testWithEnvFileInOneService(self):
        edc = EditableDockerCompose()
        service = "myservice"
        env_file_path = "/my/path"
        edc.set_service_env_file(service, env_file_path)

        with TemporaryDirectory() as tmpdir:
            edc.write_to(tmpdir)
            with open(
                os.path.join(tmpdir, "docker-compose.yml"), "r", encoding="utf8"
            ) as file:
                edc_content = yaml.load(file, Loader=yaml.Loader)

        self.assertDictEqual(
            {"services": {service: {"env_file": env_file_path}}},
            edc_content,
        )

    def testWithVolumes(self):
        edc = EditableDockerCompose()
        service = "myservice"
        volumes = ["a:b", "c:d"]
        for volume in volumes:
            edc.add_service_volume(service, volume)

        with TemporaryDirectory() as tmpdir:
            edc.write_to(tmpdir)
            with open(
                os.path.join(tmpdir, "docker-compose.yml"), "r", encoding="utf8"
            ) as file:
                edc_content = yaml.load(file, Loader=yaml.Loader)

        self.assertDictEqual(
            {"services": {service: {"volumes": volumes}}},
            edc_content,
        )
