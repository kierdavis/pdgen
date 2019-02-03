import csv
import decimal
import tempfile
import subprocess
import sys
import pathlib
from collections import namedtuple
from urllib.request import urlopen
from io import TextIOWrapper

Component = namedtuple("Component", ("refdes", "part_code", "x", "y", "rotation", "layer", "package"))

def pcb_to_xy(pcb_path, xy_path, scratch_dir_path):
  xy_path.parent.mkdir(parents=True, exist_ok=True)
  command = ["pcb", "-x", "bom", "--xyfile", str(xy_path.resolve()), str(pcb_path.resolve())]
  subprocess.run(command, check=True, cwd=scratch_dir_path)

def pcb_to_gerber(pcb_path, gerber_dir_path, scratch_dir_path):
  gerber_dir_path.mkdir(parents=True, exist_ok=True)
  base = gerber_dir_path / "board"
  command = ["pcb", "-x", "gerber", "--gerberfile", str(base.resolve()), str(pcb_path.resolve())]
  subprocess.run(command, check=True, cwd=scratch_dir_path)
  subprocess.run(["bash", "-i"], check=True, cwd=scratch_dir_path)

def strip_comments(lines):
  for line in lines:
    line = line.lstrip()
    if line and not line.startswith("#"):
      yield line

def read_components(stream):
  reader = csv.reader(strip_comments(stream))
  for row in reader:
    refdes, _description, part_code, x, y, rotation, layer = row
    if part_code == "sr-nothing":
      continue
    yield Component(
      refdes = refdes,
      part_code = part_code,
      x = decimal.Decimal(x),
      y = decimal.Decimal(y),
      rotation = int(rotation),
      layer = layer,
      package = None,
    )

def read_part_db(stream):
  db = {}
  reader = csv.reader(strip_comments(stream))
  for row in reader:
    if row[0] == "sr-nothing":
      continue
    part_code, _manufacturer, _part_number, _description, _order_number, _supplier, _per_reel, package = row
    db[part_code] = package
  return db

def look_up_packages(components, part_db):
  look_up_package = lambda component: component._replace(package = part_db[component.part_code])
  return map(look_up_package, components)

def main():
  pcb_path = pathlib.Path(sys.argv[1])
  part_db_path = pathlib.Path(sys.argv[2])

  with tempfile.TemporaryDirectory(prefix="pdgen-scratch-") as scratch_dir_path:
    scratch_dir_path = pathlib.Path(scratch_dir_path)

    gerber_dir_path = scratch_dir_path / "gerber"
    pcb_to_gerber(pcb_path, gerber_dir_path, scratch_dir_path)

    xy_path = scratch_dir_path / "components.xy"
    pcb_to_xy(pcb_path, xy_path, scratch_dir_path)
    with open(xy_path, newline="") as file:
      components = list(read_components(file))

    with open(part_db_path, newline="") as file:
      part_db = read_part_db(file)
    components = look_up_packages(components, part_db)

  for component in components:
    print(component)

if __name__ == "__main__":
  main()
