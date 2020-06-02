"""Modeue for IO functions"""
import sys


import gamelogic


class Data:
    """Class Data for load config file and get info from it"""
    data = dict()

    def __init__(self, file_name):
        self.board_size = 8

        try:
            file = open(file_name, "r")
        except FileNotFoundError:
            print("ERROR:: data file not found")
            sys.exit(1)

        for i in file:
            if len(i.strip()) == 0 or i.strip()[0] == '#':
                continue

            if i.strip() == "BOARD":
                tmp = []
                for j in range(self.board_size):
                    tmp_str = file.readline()
                    tmp.append([int(i) for i in tmp_str.strip().split()])
                self.data["BOARD"] = tmp

            if i.strip() == "BOARD_DEBUG":
                tmp = []
                for j in range(self.board_size):
                    tmp_str = file.readline()
                    tmp.append([self.data["FIGURES_DEBUG"][i] for i in tmp_str.strip().split()])
                self.data["BOARD"] = tmp

            if i.strip() == "FIGURES":
                tmp = dict()
                debug_tmp = dict()
                for j in range(13):
                    tmp_str = file.readline().split()
                    tmp[int(tmp_str[0])] = tmp_str[1]
                    debug_tmp[tmp_str[1]] = int(tmp_str[0])
                self.data["FIGURES"] = tmp
                self.data["FIGURES_DEBUG"] = debug_tmp
            if i.strip() == "FEN":
                tmp = dict()
                for j in range(13):
                    tmp_str = file.readline().split()
                    tmp[int(tmp_str[0])] = tmp_str[1]
                    debug_tmp[tmp_str[1]] = int(tmp_str[0])
                self.data["FEN"] = tmp
            if i.strip() == "BOARD_SIZE":
                self.board_size = int(file.readline().strip())

            if i.strip() == "FIGURES_COST":
                tmp = dict()
                summ = 0

                for j in range(13):
                    tmp_str = file.readline().split()
                    tmp[int(tmp_str[0])] = float(tmp_str[1])
                    summ += float(tmp_str[1])

                tmp["sum"] = summ / 2
                self.data["FIGURES_COST"] = tmp
        file.close()

    def get_figures_costs(self):
        """get_figures_costs(self) -> dict"""
        return self.data["FIGURES_COST"]

    def get_board_size(self):
        """get_board_size(self) -> Int"""
        return self.data["BOARD_SIZE"]


def print_board(board, data):
    """print_board(board, data) -> None

    prints boards in console
    """
    print()
    for i in range(data.board_size):
        print(data.board_size - i, end=" |")

        for now_fig in board[i]:
            print(data.data["FIGURES"][now_fig], end=" ")
        print()

    print("  ", end="")
    for i in range(data.board_size):
        print("---", end="")
    print()
    print("   ", end="")
    print(*[(chr(ord("a") + i) + " ") for i in range(data.board_size)])
    print()


def check_diff(start_pos, end_pos):
    return abs(start_pos[1] - end_pos[1]) > 1


def get_turn(logic, color, board, last_turn):
    """get_turn(logic, color, board) -> Turn

    Get turn from user
    """
    possible_turns = logic.generate_all_possible_turns(board, color, last_turn)

    if len(possible_turns) == 0:
        return logic.NULL_TURN

    while True:
        line = input("Please enter your turn: ").strip()
        if len(line) not in (4, 5):
            print("Wrong format")
            continue

        start_pos = (board.board_size - int(line[1]), abs(ord(line[0]) - ord("a")))
        end_pos = (board.board_size - int(line[3]), abs(ord(line[2]) - ord("a")))

        if len(line) == 5:
            figure = line[4]
            fig_num = 0
            if figure == "Q":
                fig_num = board.queen
            elif figure == "K":
                fig_num = board.knight
            elif figure == "R":
                fig_num = board.rook
            elif figure == "B":
                fig_num = board.bishop
            else:
                continue

            now_turn = gamelogic.Turn(start_pos, end_pos, color, pawn=(color*10+fig_num))

            if end_pos in possible_turns:
                if (*start_pos, now_turn.pawn) in possible_turns[end_pos]:
                    break
        else:
            if board.get_king_pos(color) == start_pos and check_diff(start_pos, end_pos):
                print(start_pos, end_pos)
                if start_pos[1] > end_pos[1]:
                    start_pos = (*start_pos, (start_pos[0], 0), (start_pos[0], 3))
                else:
                    start_pos = (*start_pos, (start_pos[0], 7), (start_pos[0], 5))

                print(start_pos, possible_turns[end_pos])
                now_turn = gamelogic.Turn(start_pos, end_pos, color, castling=True)
            elif board.get_type_map(start_pos) == board.pawn and board.get_type_map(end_pos) == board.empty_map and abs(start_pos[1] - end_pos[1]) == 1:
                now_turn = gamelogic.Turn(start_pos, end_pos, color, passant=True)
                end_pos = (*end_pos, True)
            else:
                now_turn = gamelogic.Turn(start_pos, end_pos, color)

            if end_pos in possible_turns and start_pos in possible_turns[end_pos]:
                break

        print("Wrong Turn, try again")

    return now_turn
