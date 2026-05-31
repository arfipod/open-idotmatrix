"""Create local simulator output images without hardware."""

from open_idotmatrix.protocol import build_fullscreen_color, build_pixel
from open_idotmatrix.simulator import MatrixSimulator, save_text_animation

sim = MatrixSimulator()
sim.apply_packet(build_fullscreen_color((0, 0, 0)))
sim.apply_packet(build_pixel(0, 0, (255, 0, 0)))
sim.apply_packet(build_pixel(31, 0, (0, 255, 0)))
sim.apply_packet(build_pixel(0, 31, (0, 0, 255)))
sim.apply_packet(build_pixel(31, 31, (255, 255, 255)))
sim.save("out/corners.png")

save_text_animation("open-idotmatrix", "out/text_animation.gif")
print("Wrote out/corners.png and out/text_animation.gif")
