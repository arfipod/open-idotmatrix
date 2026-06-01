from open_idotmatrix.playable_games import (
    FlappyBirdGame,
    SpaceInvadersGame,
    TetrisGame,
    available_game_names,
    create_game,
)


def _non_black_count(frame):
    image = frame.to_image()
    return sum(1 for y in range(32) for x in range(32) if image.getpixel((x, y)) != (0, 0, 0))


def test_create_game_lists_three_playable_games():
    assert available_game_names() == ("flappy", "tetris", "space_invaders")
    assert isinstance(create_game("flappy", seed=1), FlappyBirdGame)
    assert isinstance(create_game("tetris", seed=1), TetrisGame)
    assert isinstance(create_game("space_invaders", seed=1), SpaceInvadersGame)


def test_flappy_bird_flap_and_frame():
    game = FlappyBirdGame(seed=1)
    before = game.bird_y
    game.control("flap")
    frame = game.tick()

    assert game.bird_y < before
    assert frame.to_image().size == (32, 32)
    assert _non_black_count(frame) > 0


def test_tetris_moves_rotates_and_drops_piece():
    game = TetrisGame(seed=2)
    start_x = game.piece_x
    game.control("left")
    assert game.piece_x <= start_x
    game.control("rotate")
    game.control("drop")
    frame = game.tick()

    assert frame.to_image().size == (32, 32)
    assert any(any(cell is not None for cell in row) for row in game.board)


def test_space_invaders_moves_and_fires():
    game = SpaceInvadersGame(seed=3)
    start_x = game.player_x
    game.control("left")
    game.control("fire")
    frame = game.tick()

    assert game.player_x < start_x
    assert game.bullets
    assert frame.to_image().size == (32, 32)
