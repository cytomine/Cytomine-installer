# regex pattern for a UUID
import os
import pathlib
from unittest import TestCase
import zipfile

import yaml

from cytomine_installer.util import list_relative_files


UUID_PATTERN = r"[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}"


def parse_yaml(path, filename):
  with open(os.path.join(path, filename), "r", encoding="utf8") as file:
    return yaml.load(file, Loader=yaml.Loader)


def parse_dotenv(path):
  with open(path, "r", encoding="utf8") as file:
    return {
      line.split("=", 1)[0]: line.strip().split("=", 1)[1]
      for line in file.readlines()
    }


class FileSystemTestCase(TestCase):
  maxDiff = None

  def assert_is_file(self, path):
    if not pathlib.Path(path).resolve().is_file():
      raise AssertionError(f"file does not exist: {path}")

  def assert_same_text_file_content(self, path1, path2):
    self.assert_is_file(path1)
    self.assert_is_file(path2)
    with open(path1, "r", encoding="utf8") as file1, open(
      path2, "r", encoding="utf8"
    ) as file2:
      self.assertEqual(file1.read(), file2.read())

  def assert_same_yaml_file_content(self, path1, path2):
    self.assert_is_file(path1)
    self.assert_is_file(path2)
    with open(path1, "r", encoding="utf8") as file1, open(
      path2, "r", encoding="utf8"
    ) as file2:
      yml1 = yaml.load(file1, Loader=yaml.Loader)
      yml2 = yaml.load(file2, Loader=yaml.Loader)
      if yml1 is not None and yml2 is not None:
        self.assertDictEqual(yml1, yml2)
      else:
        self.assertEqual(yml1, yml2)

  def assert_same_dotenv_file_content(self, path1, path2):
    self.assert_is_file(path1)
    self.assert_is_file(path2)
    dotenv1 = parse_dotenv(path1)
    dotenv2 = parse_dotenv(path2)
    self.assertDictEqual(dotenv1, dotenv2)

  def assert_same_directories(self, gen_path, ref_path, ignored: set=None):
    if ignored is None:
      ignored = set()
    ref_rel_files = list_relative_files(ref_path)
    for out_rel_file in ref_rel_files:
      if out_rel_file in ignored:
        continue
      ref_filepath = os.path.join(ref_path, out_rel_file)
      gen_filepath = os.path.join(gen_path, out_rel_file)
      self.assert_is_file(gen_filepath)

      if out_rel_file.endswith("yml") or out_rel_file.endswith("template"):
        ### Check *.yml files
        self.assert_same_yaml_file_content(gen_filepath, ref_filepath)
      elif out_rel_file.endswith(".env"):
        self.assert_same_dotenv_file_content(gen_filepath, ref_filepath)
      else:
        self.assert_same_text_file_content(gen_filepath, ref_filepath)


class TestDeploymentGeneric(FileSystemTestCase):
  def check_single_server_deployment(self, output_ref_path, output_gen_path):
    """tests related to the tests/files/fake_single_server"""
    out_rel_files = list_relative_files(output_ref_path)
    for out_rel_file in out_rel_files:
      reference_filepath = os.path.join(output_ref_path, out_rel_file)
      generated_filepath = os.path.join(output_gen_path, out_rel_file)
      self.assert_is_file(generated_filepath)

      if os.path.basename(out_rel_file) == "cytomine.yml":
        ### Check Cytomine.yml file
        generated_content = parse_yaml(
          os.path.dirname(generated_filepath), "cytomine.yml"
        )
        reference_content = parse_yaml(
          os.path.dirname(reference_filepath), "cytomine.yml"
        )

        # need to get the autogenerated field from the generated yaml
        # but first need to check if this field exists in the generated yaml
        autogenerated_key_path = [
          "services",
          "default",
          "ims",
          "constant",
          "IMS_VAR1",
        ]
        resolved = generated_content
        for key in autogenerated_key_path:
          self.assertIn(key, resolved)
          resolved = resolved[key]

        reference_content["services"]["default"]["ims"]["constant"][
          "IMS_VAR1"
        ] = resolved

        self.assertDictEqual(generated_content, reference_content)
      elif out_rel_file.endswith("yml"):
        ### Check other *.yml files
        self.assert_same_yaml_file_content(generated_filepath, reference_filepath)
      elif out_rel_file.endswith(".env") and "ims" in os.path.basename(
        out_rel_file
      ):
        ### Check service ims.env files
        # need to replace the auto generated value !!
        reference_dotenv = parse_dotenv(reference_filepath)
        generated_dotenv = parse_dotenv(generated_filepath)
        self.assertIn("IMS_VAR1", generated_dotenv)
        reference_dotenv["IMS_VAR1"] = generated_dotenv["IMS_VAR1"]
        self.assertDictEqual(generated_dotenv, reference_dotenv)
      elif out_rel_file.endswith(".env"):
        ### Check .env file
        self.assert_same_dotenv_file_content(generated_filepath, reference_filepath)
      else:  # check configuration files
        self.assert_same_text_file_content(generated_filepath, reference_filepath)

  def check_zip(self, out_ref_path, zip_dir):
    # check there is indeed a zip
    zip_files = [f for f in os.listdir(zip_dir) if f.endswith(".zip")]
    self.assertTrue(len(zip_files), 1)
    zip_file = zip_files[0]

    with zipfile.ZipFile(
      os.path.join(zip_dir, zip_file), "r", zipfile.ZIP_DEFLATED
    ) as zip_archive:
      self.assertListEqual(
        sorted(zip_archive.namelist()),
        sorted(list_relative_files(out_ref_path)),
      )
