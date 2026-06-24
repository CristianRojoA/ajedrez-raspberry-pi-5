import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_FORCE_CPU_ONLY'] = '1'

# Pre-cargar tensor_aprendizaje ANTES de que Kivy inicie el contexto OpenGL.
# Si TF se importa por primera vez dentro de un hilo de fondo con OpenGL activo,
# el driver V3D de Broadcom (Raspberry Pi 5) hace SIGSEGV al inicializar XNNPACK.
# Al importarlo aquí, la inicialización ocurre en el hilo principal antes de OpenGL.
try:
    import tensor_aprendizaje as _ta_preload
    _ta_preload._cargar_tensorflow()
    print("[INFO] tensor_aprendizaje pre-cargado OK")
except Exception as _e:
    print(f"[WARN] Pre-carga de tensor_aprendizaje falló: {_e}")

from vista_config import *
from vista_paneles import ChatPanel, MovePanel
from vista_tablero import ChessBoard
from vista_screens_inicio import ModeScreen, MLScreen
from vista_screens_ml import EntrenarScreen, ProbarModeloScreen
from vista_screens_juego import (MenuScreen, VideoScreen, PartidasScreen,
                                 GameScreen, LoadingScreen)


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
        sm.add_widget(LoadingScreen(name='loading'))
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
