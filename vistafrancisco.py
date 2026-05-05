from vista_config import *
from vista_paneles import ChatPanel, MovePanel
from vista_tablero import ChessBoard
from vista_screens_inicio import ModeScreen, MLScreen
from vista_screens_ml import EntrenarScreen, ProbarModeloScreen
from vista_screens_juego import MenuScreen, VideoScreen, PartidasScreen, GameScreen


class ChessApp(App):
    game_mode     = 'minimax'
    ml_model_path = None
    ml_turno      = 0

    def build(self):
        self.title = "Ajedrez - Kivy"
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(ModeScreen(name='mode'))
        sm.add_widget(MLScreen(name='ml_menu'))
        sm.add_widget(EntrenarScreen(name='entrenar'))
        sm.add_widget(ProbarModeloScreen(name='probar'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(VideoScreen(name='video'))
        sm.add_widget(GameScreen(name='game'))
        sm.add_widget(PartidasScreen(name='partidas'))
        return sm

    def pause_board(self):
        game = self.root.get_screen('game')
        if hasattr(game, '_board') and game._board:
            game._board.pause()

    def resume_board(self):
        game = self.root.get_screen('game')
        if hasattr(game, '_board') and game._board:
            game._board.resume()


if __name__ == "__main__":
    ChessApp().run()
