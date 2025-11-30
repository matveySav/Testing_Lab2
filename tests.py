import pytest
import sqlite3
import os
from unittest.mock import patch
import time

class TestChessIntegration:
    @pytest.fixture
    def temp_db(self):
        name_db='chess.db'
        if os.path.exists(name_db): os.remove(name_db)
        temp_conn=sqlite3.connect(name_db)
        yield temp_conn
        temp_conn.close()
        os.remove(name_db)
        
    @pytest.fixture
    def game_setup(self):
        from Chess import Game, Player, Figure
        game = Game(side='w', player=Player('TestPlayer'))
        game.set_all_figures(reverse=True)
        return game

    @pytest.mark.parametrize("case",[1,2])
    def test_integration_move_and_checkmate(self,game_setup,temp_db,case):
        """
        Тест 1: Интеграция выполнения хода с последующим матом и окончанием игры
        Проверяет, что ход, приводящий к мату, заканчивают игру с правильным результатом (кто победил)
        """
        game = game_setup 
        game.board = [['_'] * 8 for _ in range(8)] # пустая доска
        if case == 1: # Мат белому королю двумя ладьями:
            game.move_num=1 # ход черных (нечет)
            game.set_figure(type='rook',color='black',pos=[1,0]) # черная ладья на a7
            game.set_figure(type='king',color='white',pos=[0,4]) # белый король на e8
            game.set_figure(type='rook',color='black',pos=[7,1]) # черная ладья на b1
            game.set_figure(type='king',color='black',pos=[7,7]) # черный король на h1

            game.move([7,1],[0,1]) # b1 -> b8 черной ладьей

            player,result,_,_ = game.g_history 
            assert player == game.player.get_name()
            assert result == 'black'

        else: # Мат черному королю двумя конями:
            game.move_num=0 # ход белых (чет)
            game.set_figure(type='knight',color='white',pos=[4,0]) # белый конь на a4 
            game.set_figure(type='king',color='black',pos=[0,0]) # черный король на a8
            game.set_figure(type='knight',color='white',pos=[2,2]) # белый конь на c6
            game.set_figure(type='king',color='white',pos=[1,2]) # белый король на c7

            game.move([4,0],[2,1]) # a4 -> b6 белым конем

            player,result,_,_ = game.g_history 
            assert player == game.player.get_name()
            assert result == 'white'


    @pytest.mark.parametrize("initial_pos,target_pos,_type,color",[
        ([6,0],[5,0],'pawn','white'), # a2 -> a3 белой пешкой
        ([7,1],[5,0],'knight','white'), # b1 -> a3 белым конем
        ([6,3],[4,3],'pawn','white')  # d2 -> d4 белой пешкой 
    ])
    def test_integration_move_validation_and_execution_valid(self, game_setup,temp_db, initial_pos, target_pos,_type,color):
        """
        Тест 2: Связь правил игры с выполнением хода (УСПЕШНЫЕ СЦЕНАРИИ);
        Проверяет основную игровую механику - корректность валидации и выполнения ходов (ход отражается на доске)
        + функция get_figure(position)
        """
        game = game_setup
        # Выполняем ход и проверяем его валидность (Функция проверки валидности хода, это декоратор над move)
        game.move(initial_pos, target_pos)
        # Проверяем, что фигура переместилась и значит ход был валиден
        assert game.get_figure(target_pos) != '_'
        assert game.get_figure(target_pos).type == _type
        assert game.get_figure(target_pos).color == color
        assert game.get_figure(initial_pos) == '_'


    @pytest.mark.parametrize("initial_pos,target_pos,_type,color,movenum",[
        ([1,0],[2,0],'pawn','black',0), # a7 -> a6 валидный ход черной пешкой, но ход белых 
        ([1,0],[6,0],'pawn','black',1), # a7 -> a2 нелегальный ход черной пешкой, ход черных
        ([6,3],[2,3],'pawn','white',1)  # d2 -> d6 нелегальных ход белой пешкой и ход черных
    ])
    def test_integration_move_validation_and_execution_invalid(self, game_setup,temp_db, initial_pos, target_pos,_type,color,movenum):
        """
        Тест 3: Связь правил игры с выполнением хода (ОШИБОЧНЫЕ СЦЕНАРИИ);
        Проверяет основную игровую механику - корректность валидации и выполнения ходов (ход отражается на доске)
        + функция get_figure(position)
        """
        game = game_setup
        game.move_num=movenum
        # Выполняем ход и проверяем его валидность (Функция проверки валидности хода, это декоратор над move)
        game.move(initial_pos, target_pos)
        # Проверяем, что фигура НЕ переместилась и значит ход был НЕ валиден
        assert game.get_figure(initial_pos).type == _type
        assert game.get_figure(initial_pos).color == color


    @pytest.mark.parametrize("time_passed",[30,60,90])
    def test_integration_game_result_in_database(self,game_setup,temp_db,time_passed):
        """
        Тест 4: Взаимодействие с базой данных;
        Проверяет сохранение игровых данных в БД по завершению игры
        """
        game = game_setup
        game.time_start = time.time() - time_passed
        game.move_num=1 # сейчас ход черных (нечет номер), но игра кончается значит победили белые(в моей имплементации)
        game.finish_game() # Завершаем игру (функция записи в историю и БД это декоратор над finish_game())

        conn = temp_db
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Games")
        results = cursor.fetchall()

        assert len(results) == 1
        game_record = results[0]
        assert game_record[1] == 'TestPlayer' 
        assert game_record[2] == 'white'       
        assert game_record[3] == str(time_passed)


    @pytest.mark.parametrize("time_passed",[10,100,1000])
    def test_integration_game_result_in_history(self, game_setup,temp_db,time_passed):
        """
        Тест 5: Интеграция временной системы с завершением игры и записью результата в историю;
        Проверяет корректный учет времени игры и его запись в историю по завершению
        """
        game = game_setup  
        initial_time = game.time_start        
        # Симулируем небольшое прошедшее время
        with patch('time.time') as mock_time:
            mock_time.return_value = initial_time + time_passed

            game.finish_game()
            _, _, duration, _ = game.g_history
            assert len(game.g_history) == 4
            assert duration == time_passed