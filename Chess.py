from abc import ABC, abstractmethod
import time
from threading import Thread
import threading
import sqlite3
import asyncio
import os
import tkinter as tk
from PIL import Image,ImageTk
from prettytable import PrettyTable
clear = lambda: os.system('cls')


class WrongMove(Exception):
	pass

class WrongCommand(Exception):
	pass

class ChessPlayer(ABC):
	@abstractmethod
	def get_statistics(self):
		print('return player stats and rating')
		pass
	
class ChessFigure(ABC):
	@abstractmethod
	def show(self):
		print('return the value of piece, color and type' )
		pass


class GameMixin():
	def game_time(func):
		def wrapper_finish_game(self,*args):
			func(self,*args)
			won = 'white' if self.move_num % 2 == 1 else 'black'
			self.g_history = [self.player.name,won,round(time.time() - self.time_start),time.ctime()]
			print(f'Game finished in {round(time.time() - self.time_start)} seconds')
			try: 
				with sqlite3.connect('chess.db') as conn:
					cur = conn.cursor()
					cur.execute("CREATE TABLE IF NOT EXISTS Games (GameID INTEGER PRIMARY KEY,Player_name TEXT,Result TEXT, Game_duration TEXT, Game_time TEXT)")
					cur.execute("INSERT INTO Games(Player_name,Result,Game_duration,Game_time) VALUES(?,?,?,?)", self.g_history)
				conn.close()
			except Exception as e:
				print('Database connection error: ',e) 

		return wrapper_finish_game

	def check_rules(func):
		def wrapper_move(self,*args):
			res = self.rules(*args)
			if res == 1:
				func(self,*args) # Making a move
				print(f'Move from {args[0]} to {args[1]} is valid')
			elif res == 0:
				print(f'Move from {args[0]} to {args[1]} invalid')
			else:
				func(self,*args)
				self.finish_game('Checkmate!')
		return wrapper_move

	# Before every move if check to the 'white' king
	# DO:
	#   1. For all figures('white') one by one make every possible move and check the position with is_check again.
	#   2. If all is_checks are positive then its mate to the 'white' side
	#   3. If one of the checks is negative, then it's just a check to the 'white' side
	def checkmate(self, pos): # Pos is position to the side that is BEING CHECKMATED
		current_board = Game.c_board(self.board)
		color = self.get_figure(pos).color

		for x in range(8):
			for y in range(8):
				if self.board[x][y] != '_' and self.board[x][y].color == color:
					f_moves = self.possible_moves([x,y])
					for move in f_moves:
						self.board[x][y], self.board[move[0]][move[1]] = '_', self.board[x][y]
						if not self.is_check(self.get_position('king',color)[0]):
							self.board = GameMixin.copy_board(current_board)
							return False #No checkmate
						self.board = GameMixin.copy_board(current_board)
		return True # Checkmate

	def copy_board(board):
		a = [['_' for _ in range(8)] for i in range(8)]
		for x in range(8):
			for y in range(8):
				a[x][y] = board[x][y]
		return a


	def is_check(self,pos): 
		try:
			lock = threading.Lock()
			color = self.get_figure(pos).color
			self.all_moves = []
			def get_all_moves(n,m):
				for i in range(8):
					for j in range(n,m):
						if self.board[i][j] != '_' and self.board[i][j].color != color:
							with lock:
								self.all_moves += self.possible_moves([i,j])
				return
			
			threads = [Thread(target=get_all_moves,args = i) for i in [(0,4), (4,8)]] 
			for thread in threads:
				thread.start()
			for thread in threads:
				thread.join()

			if pos in self.all_moves:
				return 1 #check
			else:
				return 0 #no check

		except Exception as e:
			print('IsCheck_erroe:',e)

	def translate_to_pos(txt):
		pos = [0]*2
		if len(txt) != 2:
			raise WrongMove('No such coordinate')
		pos[0] = 8 - int(txt[1])
		pos[1] = ord(txt[0]) - ord('a')
		if pos[0] < 0 or pos[0] > 7 or pos[1] > 7:
			raise WrongMove('No such coordinate')
		return pos

	def translate_to_str(pos):
		return chr(ord('a')+pos[1])+str(8 - pos[0])

	def set_all_figures(self,reverse = False):
		colour = ['white','black']
		if reverse:
			colour = colour[::-1]
		for t in [6,1]:
			for i in range(8):
				if t == 6:
					self.board[t][i] = Figure('pawn',colour[1])
				else:
					self.board[t][i] = Figure('pawn',colour[0])
		
		for t in [0,7]:
			for i in range(0,5):
				if t == 0:
					if i == 0:
						self.board[t][i] = Figure('rook',colour[0])
						self.board[t][7-i] = Figure('rook',colour[0])
					elif i == 1:
						self.board[t][i] = Figure('knight',colour[0])
						self.board[t][7-i] = Figure('knight',colour[0])
					elif i == 2:
						self.board[t][i] = Figure('bishop',colour[0])
						self.board[t][7-i] = Figure('bishop',colour[0])
					elif i == 3:
						self.board[t][i] = Figure('queen',colour[0])
						self.board[t][7-i] = Figure('king',colour[0])
				else:
					if i == 0:
						self.board[t][i] = Figure('rook',colour[1])
						self.board[t][7-i] = Figure('rook',colour[1])
					elif i == 1:
						self.board[t][i] = Figure('knight',colour[1])
						self.board[t][7-i] = Figure('knight',colour[1])
					elif i == 2:
						self.board[t][i] = Figure('bishop',colour[1])
						self.board[t][7-i] = Figure('bishop',colour[1])
					elif i == 3:
						self.board[t][i] = Figure('queen',colour[1])
						self.board[t][7-i] = Figure('king',colour[1])
						if colour[1] != 'white':
							self.board[t][i], self.board[t][7 - i] = self.board[t][7 - i], self.board[t][i]
							self.board[7-t][i], self.board[7-t][7 - i] = self.board[7-t][7 - i], self.board[7-t][i]

		return

	def possible_moves(self, pos, qtype = ''):
		if qtype == '':
			type = self.board[pos[0]][pos[1]].type
		else:
			type = qtype  
		color = self.board[pos[0]][pos[1]].color
		av_moves = []
		av_moves_c = []
		try:
			match type:
					case 'pawn':
						if color == 'white' and self.side == 'w' or color == 'black' and self.side == 'b':
							d = 1
						else:
							d = -1
						if pos[0] == 1 or pos[0] == 6: 
							step = 2
						else: 
							step = 1

						if self.get_figure([pos[0] - 1*d, pos[1]]) == '_':
							av_moves.append([pos[0] - 1*d, pos[1]])
						if self.get_figure([pos[0] - step*d, pos[1]]) == '_' and step == 2:
							av_moves.append([pos[0] - 2*d, pos[1]])

						if -1 < pos[1] - 1 < 7:
							if self.get_figure([pos[0]-1*d, pos[1] - 1]) != '_' and self.get_figure([pos[0]-1*d, pos[1] - 1]).color != color :
								av_moves.append([pos[0]-1*d, pos[1] - 1])
						if -1 < pos[1] + 1 < 7:
							if self.get_figure([pos[0]-1*d, pos[1] + 1]) != '_' and self.get_figure([pos[0]-1*d, pos[1] + 1]).color != color:
								av_moves.append([pos[0]-1*d, pos[1] + 1])

					case 'knight':
						for s in [-1,1]:
							for i in [1,2]:
								if 0 <= pos[0] + s*i <= 7 and 0 <= pos[1] + s*(3-i) <= 7:
									if self.get_figure([pos[0] + s*i, pos[1] + s*(3-i)]) == '_' or self.get_figure([pos[0] + s*i, pos[1] + s*(3-i)]).color != color :
										av_moves.append([pos[0] + s*i, pos[1] + s*(3-i)])
								if 0 <= pos[0] + s*i <= 7 and 0 <= pos[1] - s*(3-i) <= 7:
									if self.get_figure([pos[0] + s*i, pos[1] - s*(3-i)]) == '_' or self.get_figure([pos[0] + s*i, pos[1] - s*(3-i)]).color != color :
										av_moves.append([pos[0] + s*i, pos[1] - s*(3-i)]) 

					case 'rook':
						for d in [1,-1]:
							x, y = pos[0], pos[1]
							while 0 < x < 8 and d == -1 or -1 < x < 7 and d == 1:
								x = x + d
								if self.get_figure([x,pos[1]]) == '_':
									av_moves.append([x,pos[1]])
								else:
									if self.get_figure([x,pos[1]]).color != color:
										av_moves.append([x,pos[1]])
									break

							while  0 < y < 8 and d == -1 or -1 < y < 7 and d == 1:
								y = y + d
								if self.get_figure([pos[0],y]) == '_':
									av_moves.append([pos[0],y])
								else:
									if self.get_figure([pos[0],y]).color != color:
										av_moves.append([pos[0],y])
									break

					case 'bishop':
						x, y = pos[0], pos[1]
						for j in [-1,1]:
							flag1,flag2 = 1, 1
							for i in range(1,8):
								if flag1:
									if -1 < (x + j*i) < 8 and -1 < (y + j*i) < 8:
										if self.get_figure([x + j*i, y + j*i]) == '_':
											av_moves.append([x + j*i, y + j*i])
										else:
											if self.get_figure([x + j*i, y + j*i]).color != color:
												av_moves.append([x + j*i, y + j*i])
											flag1 = 0
								if flag2:
									if -1 < (x - j*i) < 8 and -1 < (y + j*i) < 8:
										if self.get_figure([x - j*i, y + j*i]) == '_':
											av_moves.append([x - j*i, y + j*i])
										else:
											if self.get_figure([x - j*i, y + j*i]).color != color:
												av_moves.append([x - j*i, y + j*i])
											flag2 = 0

					case 'king':
						x, y = pos[0], pos[1]
						for i in [-1,0,1]:
							for j in [-1,0,1]:
								if i == j == 0: 
									continue
								if -1 < (x+i) < 8 and -1 < (y+j) < 8:
									if self.get_figure([x+i,y+j]) == '_' or self.get_figure([x+i,y+j]).color != color:
										av_moves.append([x+i,y+j])

					case 'queen':
						av_moves += (self.possible_moves(pos,qtype = 'bishop'))
						av_moves += (self.possible_moves(pos,qtype = 'rook'))

		except Exception as e:
			print('possible_moves_error:',e)
			return []

		for i in av_moves:
			if 8 > i[0] > -1 and 8 > i[1] > -1:
				av_moves_c.append(i)
		return av_moves_c


	def c_board(board):
		a = [[0 for x in range(8)] for _ in range(8)]
		for i in range(8):
			for j in range(8):
				a[i][j] = board[i][j]
		return a


class Player(ChessPlayer):
	def __init__(self,name):
		self.name = name

	def create_player(name):
		return Player(name)

	def get_name(self):
		return self.name
	def get_statistics(self):
		pass

class Game(GameMixin):
	def __init__(self,side='w',player=Player('Default')):
		self.board = [['_'] * 8 for _ in range(8)]
		self.time_start = time.time()
		self.move_num = 0
		self.side = side
		self.player = player
		self.history = []
		self.g_history = []

	def rules(self,pos1,pos2):
		try:
			if self.board[pos1[0]][pos1[1]] == '_':
				raise WrongMove('Moving an empty spot')
			if (self.move_num % 2 == 0 and self.board[pos1[0]][pos1[1]].color == 'black' or 
				self.move_num % 2 == 1 and self.board[pos1[0]][pos1[1]].color == 'white'):
				raise WrongMove("Not your turn") 
			
			if pos2 not in self.possible_moves(pos1):
				raise WrongMove('illegal move')
			king_color = 'white' if self.move_num % 2 == 0 else 'black'
			cur_board = Game.c_board(self.board)
			
			self.board[pos1[0]][pos1[1]], self.board[pos2[0]][pos2[1]] = '_', self.board[pos1[0]][pos1[1]]
			
			if self.is_check(self.get_position('king',king_color)[0]):
				self.board = cur_board
				raise WrongMove('Moving under check')
			
			self.history.append(cur_board)
			self.move_num += 1

			king_color = 'white' if self.move_num % 2 == 0 else 'black' # checking if the last move made a check
			king_pos = self.get_position('king',king_color)[0]
			if self.is_check(king_pos):
				if self.checkmate(king_pos):
					self.board = Game.c_board(cur_board)
					return -1
				else:
					print(king_color,'check!')
			self.board = Game.c_board(cur_board)
			return 1

		except Exception as e:
			print('You made an illegal move: ',e)
		
		return 0

	def show_game(self):
		print('\n')
		for i in range(len(self.board)):
			print(8-i,end = '\t')
			for g in self.board[i]:
				print(g,end = '\t')
			print('\n')
		print('\n\t',end ='')
		for i in 'abcdefgh':
			print(i,end = '\t')
		print('\n')
		return
	
	def set_figure(self,type,pos,color):
		self.board[pos[0]][pos[1]] = Figure(type,color)
		return

	@GameMixin.check_rules
	def move(self,pos1,pos2):
		if self.board[pos1[0]][pos1[1]] != '_' and pos1 != pos2:
			self.board[pos2[0]][pos2[1]] = self.board[pos1[0]][pos1[1]]
			self.board[pos1[0]][pos1[1]] = '_'
		return

	def retract_move(self):
		try:
			if self.history:
				self.board = self.history.pop()
				self.move_num -= 1
			else:
				raise WrongCommand('No moves have happened yet')
		except Exception as e:
			print('Exception: ',e)

	@GameMixin.game_time
	def finish_game(self,str = None):
		if str:
			print(str)
		return 

	def get_figure(self,pos):
		return self.board[pos[0]][pos[1]]

	def get_position(self,type,color):
		places = []
		for i in range(8):
			for j in range(8):
				if self.board[i][j] != '_' and self.board[i][j].color == color and self.board[i][j].type == type:
					places += [[i,j]]
		return places


class Figure(ChessFigure):
	table = {'black':{'pawn': '\u2659' ,'rook': '\u2656' ,'bishop': '\u2657' ,'king': '\u2654' ,'queen': '\u2655' , 'knight': '\u2658' },\
	'white': {'pawn': '\u265F' ,'rook': '\u265C' ,'bishop': '\u265D' ,'king': '\u265A' ,'queen': '\u265B' , 'knight': '\u265E' }} 

	def __init__(self,type,color,value=0):
		self.type = type
		self.color = color
		self.value = value
		self.sname = color+'-'+type

	def __str__(self):
		return Figure.table[self.color][self.type]

	def __lt__(self, other):
		if self.value < other.value: 
			return True
		return False  

	def __gt__(self,other):
		if self.value > other.value: 
			return True
		return False  

	def show(self):
		print(self.type, self.color)


class Terminal():  
	def __init__(self):  
		self.menu_1 = {1: 'New game', 2: 'History',3: 'Player', 4: 'Change game instance', 5: 'Quit'}
		self.menu_2 = {1: 'Move', 2: 'Surrender',  3: 'Show game',4:'Retract move' , 5: 'Back to the menu'}
	
	def show_menu(self,num):
		print('\n')
		print('Game instance:',self)
		if num == 1:
			print('Player:',self.chosen_player.name)
			print('------MENU-------')
			for i in self.menu_1:
				print(i,self.menu_1[i],end='\n')

		elif num == 2:
			print('------GAME MENU-------')
			for i in self.menu_2:
				print(i,self.menu_2[i],end='\n')

	async def command_window(self):
		async def handle_new_game():
			flag = False
			txt_in = input('Choose side: w (white) or b (black) >>> ')
			if txt_in != 'w' and txt_in != 'b': 
				raise WrongCommand('Choose the right side')
			if txt_in == 'w':
				flag = True
			self.game = Game(side = txt_in, player = self.chosen_player)
			self.game.set_all_figures(reverse = flag)
			self.game.show_game()

		async def handle_player():
			try: 
				with sqlite3.connect('chess.db') as conn:
					cur = conn.cursor()
					cur.execute("CREATE TABLE IF NOT EXISTS Player (Player_id INTEGER PRIMARY KEY,Player_name TEXT)")
					cur.execute("SELECT Player_name FROM Player")
					players_db = cur.fetchall()
					print(*players_db,sep = '\n')
					print('Choose your player account, or create a new one (enter </create <player_nickname> > )')
					txt_in = input('>>>').split()
					if '/create' in txt_in and len(txt_in) == 2:
						for t in players_db:
							if t[0] == txt_in[1]:
								raise WrongCommand('Player already exists') 
						self.chosen_player = Player(txt_in[1])
						cur.execute("INSERT INTO Player(Player_name) VALUES(?)", (self.chosen_player.name,))
					elif txt_in[0] in [i[0] for i in players_db]:
						self.chosen_player = Player(txt_in[0])
					else:
						raise WrongCommand('Incorrect name for a player')
				conn.close()

			except Exception as e:
				print('Database connection error: ',e)

		async def handle_move():
			moves = input('Enter your move >> ').split()
			if len(moves) != 2: 
				raise WrongCommand('Wrong amount of arguments for the move')
			self.game.move(GameMixin.translate_to_pos(moves[0]),GameMixin.translate_to_pos(moves[1]))
			self.game.show_game()

		async def handle_retract_move():
			self.game.retract_move()
			self.game.show_game()

		async def handle_history():
			try: 
				with sqlite3.connect('chess.db') as conn:
					cur = conn.cursor()
					cur.execute("CREATE TABLE IF NOT EXISTS Games (GameID INTEGER PRIMARY KEY,Player_name TEXT,Result TEXT, Game_duration TEXT, Game_time TEXT)")
					cur.execute("SELECT * FROM Games")
					res = cur.fetchall()
					print('GameID Player_name Result(win) Game_duration(seconds) Game_time'.replace(' ', '\t\t'))
					for game_res in res:
						print('\t\t'.join(str(x) for x in game_res))
				conn.close()
			except Exception as e:
				print('Database connection error: ',e) 
		
		menu_num = 1
		self.chosen_player = Player('Default')
		while 1:
			try:
				self.show_menu(menu_num)
				txt_in = input('>>>')
				command_num = int(txt_in)
				if menu_num == 1:
					if command_num not in self.menu_1:
						raise WrongCommand('Wrong command number')
					if command_num == 1:
						await handle_new_game()
						menu_num = 2
					elif command_num == 2:
						await handle_history()
					elif command_num == 3:
						await handle_player()
					elif command_num == 4:
						await asyncio.sleep(1)
					elif command_num == 5:
						return #Console exit

				elif menu_num == 2:
					if command_num not in self.menu_2:
						raise WrongCommand('Wrong command number')
					elif command_num == 1:
						await handle_move()
					elif command_num == 2:
						self.game.finish_game()
						menu_num = 1 
					elif command_num == 3:
						self.game.show_game()
					elif command_num == 4:
						await handle_retract_move()
					elif command_num == 5:
						menu_num = 1

			except Exception as e:
				print('Exception:',e)

class ChessApp():

	def set_board(self):
		if self.board_canvas:
			self.board_canvas.delete('all')
		self.table_id = [[0 for y in range(8)] for x in range(8)]
		for i in range(8):
			color = "white" if i % 2 == 0 else "gray"
			for j in range(8):
				x0 = j * 50
				y0 = i * 50
				x1 = x0 + 50
				y1 = y0 + 50
				square_id = self.board_canvas.create_rectangle(x0, y0, x1, y1, fill=color)
				self.table_id[i][j] = square_id
				self.board_canvas.tag_bind(square_id, "<Button-1>", lambda event, square_id=square_id, square_id_pos = i*8+j+1: self.select_square(square_id,square_id_pos))
				if self.game.board[i][j] != '_':
					pic_id = self.board_canvas.create_image(j*50+25,i*50+25,image = self.imgs[color[0]+self.game.board[i][j].sname])
					self.board_canvas.tag_bind(pic_id, "<Button-1>", lambda event,square_id = square_id,square_id_pos = i*8+j+1: self.select_square(square_id,square_id_pos))
				color = "white" if color == "gray" else "gray"

	def __init__(self, master):
		self.game = Game()
		self.game.set_all_figures(reverse=True)
		self.master = master
		self.master.minsize(width=400, height=430)
		self.master.maxsize(width=400, height=430)
		# C://Users//sta30//Downloads//Учеба//PROG//
		self.master.title("Chess App")
		self.board_canvas = tk.Canvas(master, width=400, height=400,bg = 'black')
		self.board_canvas.pack()
		self.selected_square = None
		self.lock = 0
		
		def read_imgs():
			piece = ['rook','king','queen','knight','bishop','pawn']
			d = 'Chess_img//' 
			b = 'black-'; w = 'white-'
			orig = []
			for c1 in ['g','w']:
				for c2 in [b,w]:
					orig += [(c1+c2+x,Image.open(d + c1 + c2 + x + '.png')) for x in piece]
			resized = []
			for name,img in orig:
				resized += [(name,ImageTk.PhotoImage(img.resize((32,32))))]
			self.imgs = dict(resized)
		read_imgs()

		self.set_board()

		def handle_buttons():
			self.line = tk.Label(master, text = '')
			self.line.pack()
		handle_buttons()

		def handle_menu():
			def popup():
			   top = tk.Toplevel(self.master)
			   top.title("Pop-up")
			   tk.Label(top, text= "Создано Матвеем Савальским 409489",font = "Gothic").pack()
		  
			self.menu = tk.Menu(master)
			master.config(menu=self.menu)

			filemenu = tk.Menu(self.menu,tearoff = 0)
			filemenu.add_command(label="История",command = self.get_history)
			filemenu.add_command(label="Игроки",command = self.get_players)
			filemenu.add_command(label="Выход",command = self.quit_game)

			gamemenu = tk.Menu(self.menu, tearoff = 0)
			gamemenu.add_command(label='Черными',command = self.set_clean_black)
			gamemenu.add_command(label='Белыми',command = self.set_clean_white)
			
			opmenu = tk.Menu(self.menu,tearoff=0)
			opmenu.add_command(label="Ход назад", command = self.retract)
			opmenu.add_command(label="Сдаться", command = self.srndr)
			opmenu.add_command(label="Продолжить игру", command = self.unlock)

			helpmenu = tk.Menu(self.menu, tearoff=0)
			helpmenu.add_command(label="О программе",command = popup)

			self.menu.add_cascade(label="Файл", menu=filemenu)
			self.menu.add_cascade(label="Новая игра", menu = gamemenu)
			self.menu.add_cascade(label="Операции", menu=opmenu)
			self.menu.add_cascade(label="Справка", menu=helpmenu)

		handle_menu()
	def unlock(self):
		self.lock = 0
	def select_square(self,square_id,square_id_pos):
		if not self.lock:
			color = 'white' if self.game.move_num%2 ==0 else 'black'
			if self.selected_square:
				self.game.move(self.last_move,ChessApp.convert(square_id_pos))
				self.set_board()
				color = 'white' if self.game.move_num%2 ==0 else 'black'
				king_pos=self.game.get_position('king',color)[0]
				if self.game.checkmate(king_pos):
					self.line.configure(text=f'Checkmate! Game finished in {round(time.time() - self.game.time_start)} seconds')
					self.lock = 1
					return
				self.selected_square = None

			else:
				self.selected_square = square_id
				self.last_move = ChessApp.convert(square_id_pos)
				self.board_canvas.itemconfig(self.selected_square, outline="red",width=2)
				color = 'white' if self.game.move_num%2 ==0 else 'black'
				if self.game.board[self.last_move[0]][self.last_move[1]] != '_' and self.game.board[self.last_move[0]][self.last_move[1]].color == color :
					moves = self.game.possible_moves(self.last_move)
					for m1,m2 in moves:
						self.board_canvas.itemconfig(self.table_id[m1][m2], outline="green",width=2)
			self.line.configure(text=f'Выбрана клетка: {Game.translate_to_str(ChessApp.convert(square_id_pos))}')
	
	def convert(x):
		return [(x-1)//8,(x-1)%8]

	def retract(self):
		self.game.retract_move()
		self.set_board()
		self.lock = 0

	def set_clean_black(self):
		self.game = Game(side = 'b')
		self.game.set_all_figures(reverse=False)
		self.lock = 0
		self.set_board()
	def set_clean_white(self):
		self.game = Game(side='w')
		self.game.set_all_figures(reverse=True)
		self.lock = 0
		self.set_board()

	def get_history(self):
		try: 
			with sqlite3.connect('chess.db') as conn:
				cur = conn.cursor()
				cur.execute("CREATE TABLE IF NOT EXISTS Games (GameID INTEGER PRIMARY KEY,Player_name TEXT,Result TEXT, Game_duration TEXT, Game_time TEXT)")
				cur.execute("SELECT * FROM Games")
				res = cur.fetchall()
				table = PrettyTable()
				table.field_names ='GameID Player_name Result(win) Game_duration(seconds) Game_time'.split()
				for i in res:
					table.add_row(i)
			conn.close()

		except Exception as e:
			print('Database connection error: ',e) 

		top = tk.Toplevel(self.master)
		top.title("Game history")
		top.minsize(width=550, height=400)
		canvas = tk.Canvas(top,scrollregion=(-1000,-1000,10000,10000))
		canvas.create_text(270,370,text = table)

		scrollbar = tk.Scrollbar(top, orient = 'vertical')
		scrollbar.pack(side='right', fill='y')
		scrollbar.config(command=canvas.yview)

		canvas.config(yscrollcommand=scrollbar.set)
		canvas.pack(side='left', fill='both', expand=True)

	def get_players(self):
		try: 
			with sqlite3.connect('chess.db') as conn:
				cur = conn.cursor()
				cur.execute("CREATE TABLE IF NOT EXISTS Player (Player_id INTEGER PRIMARY KEY,Player_name TEXT)")
				cur.execute("SELECT Player_name FROM Player")
				players_db = cur.fetchall()
			conn.close()
		except Exception as e:
			print('Database connection error: ',e)

		top = tk.Toplevel(self.master)
		top.minsize (width = 200, height = 100)
		top.title("Player List")

		var = tk.StringVar(value = self.game.player.name)
		def set_player():
			self.game.player = Player(var.get())
		for player in players_db:
			tk.Radiobutton(top,text=player[0],value = player[0], variable = var, command = set_player).pack()

	def srndr(self):
		if not self.lock:
			self.game.finish_game()
			color = 'white' if self.game.move_num%2 ==0 else 'black'
			self.line.configure(text = f'{color} surrendered in {round(time.time()-self.game.time_start)} seconds')
			self.lock = 1
	def quit_game(self):
		self.master.destroy()

class StartProgramm():
	def __init__(self):
		while 1:
			txt = input('Введите\n1 для игры в консоли\n2 для запуска с граф. интерфейсом\n>>> ')
			try:
				if int(txt) == 1 or int(txt) == 2:
					break
				else:
					raise Exception
			except:
				print('Ошибка ввода, выберите снова ')

		if int(txt) == 1:
			t = Terminal()
			# # t2 = Terminal()
			async def main():
				task1 = asyncio.create_task(t.command_window())
			# 	# task2 = asyncio.create_task(t2.command_window())
				await task1
			# 	# await task2
			asyncio.run(main())

		else:
			root = tk.Tk()
			app = ChessApp(root)
			root.mainloop()

if __name__ == '__main__':
	StartProgramm()