"""Génère les supports imprimables de SpaceFarm 2080 dans FreeCAD.

Exécution : FreeCADCmd cad/SpaceFarm_2080.py
Les fichiers sont créés dans cad/output.
"""
import os

import FreeCAD as App
import Part
import Mesh


# ---------- Dimensions à vérifier sur le matériel (millimètres) ----------
WALL = 2.4
CLEARANCE = 0.4
M3_HOLE = 3.4

YUN_LENGTH = 68.6
YUN_WIDTH = 53.4
YUN_HOLES = [(2.5, 15.2), (15.2, 50.8), (66.0, 7.6), (66.0, 35.6)]

BREADBOARD_LENGTH = 83.0       # À mesurer
BREADBOARD_WIDTH = 55.0        # À mesurer
BREADBOARD_HEIGHT = 9.5        # À mesurer

RPI_LENGTH = 85.0
RPI_WIDTH = 56.0
RPI_HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]

DHT_WIDTH = 12.0
DHT_HEIGHT = 15.5
DHT_DEPTH = 5.5

LIGHT_MODULE_WIDTH = 22.0      # À mesurer
LIGHT_MODULE_HEIGHT = 30.0     # À mesurer

WATER_SENSOR_WIDTH = 20.0      # À mesurer
WATER_SENSOR_THICKNESS = 1.6   # À mesurer
RESERVOIR_WALL = 3.0           # À mesurer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def rounded_plate(length, width, height, radius=4.0):
    """Plaque rectangulaire avec angles arrondis."""
    radius = min(radius, length / 2, width / 2)
    shape = Part.makeBox(length - 2 * radius, width, height, App.Vector(radius, 0, 0))
    shape = shape.fuse(Part.makeBox(length, width - 2 * radius, height, App.Vector(0, radius, 0)))
    for x in (radius, length - radius):
        for y in (radius, width - radius):
            shape = shape.fuse(Part.makeCylinder(radius, height, App.Vector(x, y, 0)))
    return shape


def standoff(x, y, height=6.0, outer=6.5, hole=M3_HOLE):
    outer_shape = Part.makeCylinder(outer / 2, height, App.Vector(x, y, 0))
    bore = Part.makeCylinder(hole / 2, height + 1, App.Vector(x, y, -0.5))
    return outer_shape.cut(bore)


def add_mounting_holes(shape, length, width, margin=7.0):
    for x in (margin, length - margin):
        for y in (margin, width - margin):
            hole = Part.makeCylinder(M3_HOLE / 2, WALL + 2, App.Vector(x, y, -1))
            shape = shape.cut(hole)
    return shape


def arduino_breadboard_base():
    """Socle principal avec entretoises Yún et rails pour breadboard."""
    margin = 10.0
    gap = 14.0
    length = margin * 2 + YUN_LENGTH + gap + BREADBOARD_LENGTH
    width = margin * 2 + max(YUN_WIDTH, BREADBOARD_WIDTH)
    shape = rounded_plate(length, width, WALL, 6)
    shape = add_mounting_holes(shape, length, width)

    yun_x = margin
    yun_y = (width - YUN_WIDTH) / 2
    for hx, hy in YUN_HOLES:
        shape = shape.fuse(standoff(yun_x + hx, yun_y + hy, 6.0))

    board_x = margin + YUN_LENGTH + gap
    board_y = (width - BREADBOARD_WIDTH) / 2
    rail_h = BREADBOARD_HEIGHT / 2
    rail_t = 2.4
    shape = shape.fuse(Part.makeBox(BREADBOARD_LENGTH + 2 * CLEARANCE,
                                    rail_t, rail_h,
                                    App.Vector(board_x - CLEARANCE, board_y - rail_t - CLEARANCE, WALL)))
    shape = shape.fuse(Part.makeBox(BREADBOARD_LENGTH + 2 * CLEARANCE,
                                    rail_t, rail_h,
                                    App.Vector(board_x - CLEARANCE,
                                               board_y + BREADBOARD_WIDTH + CLEARANCE, WALL)))

    # Deux passages pour les faisceaux USB et capteurs.
    for x in (yun_x + YUN_LENGTH + 3, board_x - 7):
        slot = rounded_plate(10, 28, WALL + 2, 3)
        slot.translate(App.Vector(x, width / 2 - 14, -1))
        shape = shape.cut(slot)
    return shape


def raspberry_case():
    """Boîtier ouvert : carte ventilée et connecteurs accessibles."""
    inner_l = RPI_LENGTH + 2 * CLEARANCE
    inner_w = RPI_WIDTH + 2 * CLEARANCE
    outer_l = inner_l + 2 * WALL
    outer_w = inner_w + 2 * WALL
    height = 18.0
    outer = rounded_plate(outer_l, outer_w, height, 5)
    cavity = Part.makeBox(inner_l, inner_w, height,
                          App.Vector(WALL, WALL, WALL))
    shape = outer.cut(cavity)

    # Grandes ouvertures latérales pour USB/Ethernet, alimentation et HDMI.
    shape = shape.cut(Part.makeBox(34, WALL + 2, 13,
                                   App.Vector(outer_l - 48, -1, 5)))
    shape = shape.cut(Part.makeBox(28, WALL + 2, 10,
                                   App.Vector(12, outer_w - WALL - 1, 5)))
    shape = shape.cut(Part.makeBox(WALL + 2, 26, 10,
                                   App.Vector(-1, outer_w - 38, 5)))

    # Ventilation sous la carte.
    for x in range(18, int(outer_l - 12), 12):
        vent = Part.makeBox(6, 24, WALL + 2, App.Vector(x, outer_w / 2 - 12, -1))
        shape = shape.cut(vent)

    for hx, hy in RPI_HOLES:
        shape = shape.fuse(standoff(WALL + CLEARANCE + hx,
                                    WALL + CLEARANCE + hy, 5.5, 6.0, 2.8))
    return shape


def dht11_holder():
    """Support ajouré avec petit toit anti-éclaboussures."""
    foot_l = 38.0
    foot_w = 28.0
    shape = rounded_plate(foot_l, foot_w, WALL, 4)
    back_y = foot_w - WALL
    back = Part.makeBox(foot_l, WALL, DHT_HEIGHT + 12,
                        App.Vector(0, back_y, WALL))
    window = Part.makeBox(DHT_WIDTH + 5, WALL + 2, DHT_HEIGHT - 4,
                          App.Vector((foot_l - DHT_WIDTH - 5) / 2, back_y - 1, WALL + 6))
    shape = shape.fuse(back.cut(window))

    pocket_w = DHT_WIDTH + CLEARANCE
    left_x = (foot_l - pocket_w) / 2 - WALL
    shape = shape.fuse(Part.makeBox(WALL, DHT_DEPTH + 2, DHT_HEIGHT + 2,
                                    App.Vector(left_x, back_y - DHT_DEPTH - 2, WALL + 3)))
    shape = shape.fuse(Part.makeBox(WALL, DHT_DEPTH + 2, DHT_HEIGHT + 2,
                                    App.Vector(left_x + pocket_w + WALL,
                                               back_y - DHT_DEPTH - 2, WALL + 3)))
    roof = Part.makeBox(pocket_w + 2 * WALL, DHT_DEPTH + 7, WALL,
                        App.Vector(left_x, back_y - DHT_DEPTH - 5, WALL + DHT_HEIGHT + 7))
    shape = shape.fuse(roof)
    return add_mounting_holes(shape, foot_l, foot_w, 5)


def light_sensor_holder():
    """Équerre orientable, serrée par une vis M3 de chaque côté."""
    foot_l = 44.0
    foot_w = 30.0
    shape = rounded_plate(foot_l, foot_w, WALL, 4)
    plate_w = LIGHT_MODULE_WIDTH + 8
    plate_h = LIGHT_MODULE_HEIGHT + 8
    plate = Part.makeBox(plate_w, WALL, plate_h,
                         App.Vector((foot_l - plate_w) / 2, foot_w - WALL, WALL))
    aperture = Part.makeCylinder(6, WALL + 2,
                                 App.Vector(foot_l / 2, foot_w - WALL - 1,
                                            WALL + plate_h / 2), App.Vector(0, 1, 0))
    shape = shape.fuse(plate.cut(aperture))
    for x in ((foot_l - plate_w) / 2 + 5, (foot_l + plate_w) / 2 - 5):
        hole = Part.makeCylinder(M3_HOLE / 2, WALL + 2,
                                 App.Vector(x, foot_w - WALL - 1, WALL + 6), App.Vector(0, 1, 0))
        shape = shape.cut(hole)
    return add_mounting_holes(shape, foot_l, foot_w, 5)


def water_sensor_clip():
    """Pince de bord de réservoir et glissière verticale pour la sonde."""
    clip_w = 38.0
    clip_d = 18.0
    clip_h = 42.0
    shape = Part.makeBox(clip_w, clip_d, clip_h)

    # Fente montant sur la paroi du réservoir, ouverte par le bas.
    wall_slot = Part.makeBox(RESERVOIR_WALL + CLEARANCE,
                             clip_d + 2, clip_h - WALL,
                             App.Vector(8, -1, 0))
    shape = shape.cut(wall_slot)

    # Glissière pour la carte : l’électronique reste au-dessus de l’eau.
    sensor_x = 17.0
    channel = Part.makeBox(WATER_SENSOR_WIDTH + CLEARANCE,
                           WATER_SENSOR_THICKNESS + CLEARANCE,
                           clip_h - 8,
                           App.Vector(sensor_x, (clip_d - WATER_SENSOR_THICKNESS) / 2, 0))
    shape = shape.cut(channel)
    cable_slot = Part.makeBox(8, clip_d + 2, 14,
                              App.Vector(clip_w - 10, -1, clip_h - 14))
    return shape.cut(cable_slot)


def cable_comb():
    """Petit peigne pour six câbles Dupont."""
    shape = rounded_plate(42, 12, 5, 3)
    for index in range(6):
        x = 6 + index * 6
        hole = Part.makeCylinder(1.4, 7, App.Vector(x, 6, -1))
        shape = shape.cut(hole)
        opening = Part.makeBox(1.8, 7, 7, App.Vector(x - 0.9, 6, -1))
        shape = shape.cut(opening)
    return shape


def export_shape(shape, filename):
    temporary = document.addObject('Part::Feature', 'ExportTemporary')
    temporary.Shape = shape
    document.recompute()
    Mesh.export([temporary], os.path.join(OUTPUT_DIR, filename))
    document.removeObject(temporary.Name)


document = App.newDocument('SpaceFarm2080')
parts = [
    ('ArduinoBreadboardBase', '01_socle_arduino_breadboard.stl', arduino_breadboard_base()),
    ('RaspberryPiCase', '02_boitier_raspberry_pi.stl', raspberry_case()),
    ('DHT11Holder', '03_support_dht11.stl', dht11_holder()),
    ('LightSensorHolder', '04_support_luminosite.stl', light_sensor_holder()),
    ('WaterSensorClip', '05_pince_capteur_eau.stl', water_sensor_clip()),
    ('CableComb', '06_peigne_cables.stl', cable_comb()),
]

offset_x = 0
for name, filename, shape in parts:
    export_shape(shape, filename)
    obj = document.addObject('Part::Feature', name)
    obj.Label = name
    obj.Shape = shape
    obj.Placement.Base = App.Vector(offset_x, 0, 0)
    offset_x += shape.BoundBox.XLength + 18

document.recompute()
document.saveAs(os.path.join(OUTPUT_DIR, 'SpaceFarm_2080.FCStd'))
print('SpaceFarm : fichiers générés dans ' + OUTPUT_DIR)
