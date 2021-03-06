"""Class Logic and class Turn module"""
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=arguments-out-of-order
# pylint: disable=undefined-variable

from collections import defaultdict
from itertools import product
from multiprocessing import Process
from multiprocessing import Manager

import PythonChess.generate_turns as gt
from .board import Board
from .turns import Turn


class Logic:
    """main Logic class for game logic realisation"""
    MAX_COST = 9999
    MIN_COST = -9999
    NULL_TURN = Turn((-1, -1), (-1, -1), 0)
    turn_history = list()

    def __init__(self, data, num_threads, evaluation, debuts):
        print(_("Init game logic class"))
        self.figures_cost = data.data["FIGURES_COST"]
        self.av_threads = num_threads
        self.evaluation = evaluation
        self.debuts = debuts
        self.flag = True

    def add_turn_to_history(self, now_turn):
        """Ddds turn for history

        :param now_turn: turn to add
        :type now_turn: class Turn object
        """

        self.turn_history.append(now_turn)

    def get_turn_from_history(self, index):
        """Returns turn from history

        :param index: point in history
        :type index: int
        :return: turn at index
        :rtype: class Turn object
        """
        return self.turn_history[index]

    def generate_turns(self, board, color, last_turn):
        """Generates possible turns

        :param board: board object
        :type board: class board object
        :param color: color
        :type color: int
        :param last_turn: previous turn
        :type last_turn: class Turn object
        :return: list of possible turns
        :rtype: list(class Turn object)
        """
        possible_turns = self.generate_all_possible_turns(board, color, last_turn)
        turns = list()

        for end_pos in possible_turns:
            for start_pos in possible_turns[end_pos]:
                if len(start_pos) == 3:
                    now_turn = Turn((start_pos[0], start_pos[1]), end_pos, color, start_pos[2])
                elif len(start_pos) == 4:
                    now_turn = Turn(start_pos, end_pos, color, castling=True)
                elif len(end_pos) == 3:
                    now_turn = Turn(start_pos, end_pos[:2], color, passant=True)
                else:
                    now_turn = Turn(start_pos, end_pos, color)

                turns.append(now_turn)

        return turns

    def generate_all_possible_turns(self, board, color, last_turn, check_check=True):
        """ Generates all possible turns

        :param board: board object
        :type board: class board object
        :param color: color
        :type color: int
        :param last_turn: previous turn
        :type last_turn: class Turn object
        :param check_check: nessesity to check check, defaults to True
        :type check_check: bool, optional
        :return: returns all possible turns in dict
        :rtype: dict(tuple: {dict(tuple: {list()})})
        """

        if check_check:
            opponent_turns, opponent_turns_for_king = (
                self.generate_all_possible_turns(board, 3 - color, self.NULL_TURN,
                                                 check_check=False))

        possible_turns = defaultdict(list)
        turns_for_king = defaultdict(list)
        # dict key = position of possible turn
        # dict value = list of positions where from this turn can be done

        for pos in product(range(board.board_size), repeat=2):
            if board.get_color_map(pos) == color:
                if board.get_type_map(pos) == board.pawn:
                    gt.generate_turns_pawn(pos, board, possible_turns, color, turns_for_king)

                if board.get_type_map(pos) == board.knight:
                    gt.generate_turns_knight(pos, board, possible_turns, color, turns_for_king)

                if board.get_type_map(pos) == board.rook:
                    gt.generate_turns_rook(pos, board, possible_turns, color, turns_for_king)

                if board.get_type_map(pos) == board.bishop:
                    gt.generate_turns_bishop(pos, board, possible_turns, color, turns_for_king)

                if board.get_type_map(pos) == board.queen:
                    gt.generate_turns_queen(pos, board, possible_turns, color, turns_for_king)

                if board.get_type_map(pos) == board.king:
                    if check_check:
                        gt.generate_turns_king(pos, board, possible_turns, color,
                                               opponent_turns, opponent_turns_for_king)
                    else:
                        gt.generate_turns_king(pos, board, possible_turns, color,
                                               defaultdict(list), defaultdict(list))
        gt.check_de_passant(board, possible_turns, last_turn, color)

        if check_check:
            king_pos = board.get_king_pos(color)
            possible_turns = gt.remove_not_possible_turns(board, king_pos, color,
                                                          possible_turns, opponent_turns,
                                                          opponent_turns_for_king)
            return possible_turns

        return (possible_turns, turns_for_king)

    def thread_generate(self, board, color, depth, turns, index, return_dict):
        """Makes AI turn depp calculations

        :param board: board object
        :type board: class board object
        :param color: color
        :type color: int
        :param depth: depth of calculations
        :type depth: int
        :param turns: possible turns
        :type turns: list(class Turn object)
        :param index: process index
        :type index: int
        :param return_dict: tuple of best_turn and it cost
        :type return_dict: (class Turn object, int)
        """
        best_cost = self.MIN_COST
        best_turn = self.NULL_TURN
        alpha = self.MIN_COST
        beta = self.MAX_COST
        for now_turn in turns:
            tmp, flags = board.do_turn(now_turn)

            now_cost = -self.ai_turn(board, 3 - color, depth - 1, now_turn, [beta], [alpha])[1]

            board.un_do_turn(now_turn, tmp, flags)
            if now_cost >= best_cost:
                best_cost = now_cost
                best_turn = now_turn

            if color == board.black:
                alpha = max(alpha, best_cost)
            else:
                beta = min(beta, best_cost)

            if beta <= alpha:
                break

        return_dict[index] = (best_turn, best_cost)

    def root_ai_turn(self, board, color, depth, last_turn):
        """Starts AI turn calculation

        :param board: board object
        :type board: class board object
        :param color: color
        :type color: int
        :param depth: depth of calculations
        :type depth: int
        :param last_turn: last turn
        :type last_turn: class Turn object
        :return: tuple of best_turn and it cost
        :rtype: (class Turn object, int)
        """

        if last_turn in self.debuts.next_turns and self.flag:
            self.debuts = self.debuts.next_turns[last_turn]
        elif last_turn == self.NULL_TURN and len(self.debuts.next_turns) != 0:
            best_turn = self.debuts.sorted_turns[0][0]
            self.debuts = self.debuts.next_turns[best_turn]
            if board.flipped:
                best_turn.rotate()
            return (best_turn, 0)
        else:
            self.flag = False
        if len(self.debuts.next_turns) == 0:
            self.flag = False
        elif self.flag:
            best_turn = self.debuts.sorted_turns[0][0]
            self.debuts = self.debuts.next_turns[best_turn]
            if board.flipped:
                best_turn.rotate()
            return (best_turn, 0)

        manager = Manager()
        return_dict = manager.dict()

        turns = self.generate_turns(board, color, last_turn)
        threads = []
        num_of_threads = self.av_threads
        if len(turns) // self.av_threads == 0:
            num_of_threads = len(turns)

        all_turns = list()
        for i in range(num_of_threads):
            tmp_turns = list()
            for now in turns[i::num_of_threads]:
                tmp_turns.append(now)
            all_turns.append(tmp_turns)

        for i in range(num_of_threads):
            now_board = Board(None, board)

            threads.append(Process(target=self.thread_generate, name=len(threads),
                                   args=(now_board, color, depth,
                                         all_turns[i], i, return_dict)))

            threads[len(threads) - 1].start()

        for thread in threads:
            thread.join()
        return max(return_dict.values(), key=lambda x: x[1])

    def ai_turn(self, board, color, depth, last_turn, alpha, beta):
        """

        :param board: board object
        :type board: class board object
        :param color: color
        :type color: int
        :param depth: depth of calculations
        :type depth: int
        :param last_turn: last turn
        :type last_turn: class Turn object
        :param alpha: alpha, defaults to MIN_COST
        :type alpha: int, optional
        :param beta: beta, defaults to MAX_COST
        :type beta: int, optional
        :return: tuple of best_turn and it cost
        :rtype: (class Turn object, int)
        """
        alpha[0] = -alpha[0]
        beta[0] = -beta[0]
        turns = self.generate_turns(board, color, last_turn)

        best_cost = self.MIN_COST
        best_turn = self.NULL_TURN

        for now_turn in turns:
            tmp, flags = board.do_turn(now_turn)

            if depth == 1:
                now_cost = self.evaluation.evaluate_board_mg(board, color)
            else:
                now_cost = -self.ai_turn(board, 3 - color, depth - 1, now_turn, beta, alpha)[1]

            board.un_do_turn(now_turn, tmp, flags)
            if now_cost >= best_cost:
                best_cost = now_cost
                best_turn = now_turn

            if color == board.black:
                alpha[0] = max(alpha[0], best_cost)
            else:
                beta[0] = min(beta[0], best_cost)

            if beta[0] <= alpha[0]:
                break

        alpha[0] = -alpha[0]
        beta[0] = -beta[0]
        return (best_turn, best_cost)
