from open_idotmatrix.protocol import build_fullscreen_color, build_pixel, build_text_packet
from open_idotmatrix.simulator import MatrixSimulator, simulate_text_frame
from open_idotmatrix.text import render_text_bitmap_bytes


def test_simulator_fill_and_pixel_packets():
    sim = MatrixSimulator()
    sim.apply_packet(build_fullscreen_color((1, 2, 3)))
    assert sim.pixels[0][0] == (1, 2, 3)
    sim.apply_packet(build_pixel(31, 31, (255, 0, 0)))
    assert sim.pixels[31][31] == (255, 0, 0)


def test_simulator_text_packet_renders_non_empty_image():
    bitmaps = render_text_bitmap_bytes("A")
    packet = build_text_packet(bitmaps, text_color=(255, 255, 255))
    sim = MatrixSimulator()
    sim.apply_packet(packet)
    img = sim.to_image()
    assert img.size == (32, 32)
    assert any(img.getpixel((x, y)) != (0, 0, 0) for x in range(32) for y in range(32))


def test_simulate_text_frame():
    sim = simulate_text_frame("Hi")
    assert sim.to_image(scale=2).size == (64, 64)
