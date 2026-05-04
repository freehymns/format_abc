import re
from fractions import Fraction
import sys

ENCODING = "iso-8859-1"

#
# This code is derived from the abc_search and aligner modules
# of EasyABC (https://sourceforge.net/projects/easyabc/)
#
# Copyright (C) 2011-2014 Nils Liberg (mail: kotorinl at yahoo.co.uk)
# Copyright (C) 2015-2024 Seymour Shlien (mail: fy733@ncf.ca), Jan Wybren de Jong (jw_de_jong at yahoo dot com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

DEFAULT_LENGTH = 'mcm_default'

repl_by_spaces = lambda m: ' ' * len(m.group(0))

bar_sep_symbols = ':|][|: :|[2 :|]2 :||: [|] :|] [|: :|| ||: :|: |:: ::| |[1 :|2 |] || [| :: .| |1 |: :| [1 [2 |'.split()

note_pattern = r"(?P<note>([_=^]?[A-Ga-gxz](,+|'+)?))(?P<length>\d{0,3}(?:/\d{0,3})*)(?P<dot>\.*)(?P<broken>[><]?)"
tuplet_pattern = r"\((?P<p>[1-9])(?:\:(?P<q>[1-9]?))?(?:\:(?P<r>[1-9]?))?" # put p notes into the time of q for the next r notes

def get_default_len(abc):
    if re.search(r'(?m)^L: *mcm_default', abc):
        return DEFAULT_LENGTH
    else:
        m = re.search(r'(?m)^L: *(\d+)/(\d+)', abc)
        if m:
            return Fraction(int(m.group(1)), int(m.group(2)))
        else:
            return Fraction(1, 8)

def get_metre(abc):
    m = re.search(r'(?m)^M: *(\d+)/(\d+)', abc)
    if m:
        return Fraction(int(m.group(1)), int(m.group(2)))
    else:
        return Fraction(4, 4)

def simplify_bars(abc):
    # replace bar symbols with spaces and one simple bar line
	for sym in bar_sep_symbols:
		clean_sym = ""
		found_bar = False
		for i in range(len(sym)):
			clean_sym += ("|" if sym[i] == "|" and (not found_bar) else " ")
			if sym[i] == "|":
				found_bar = True
		abc = abc.replace(sym, clean_sym)
	return abc

def remove_non_note_fragments(abc):
    # replace non-note fragments of the text by replacing them by spaces (thereby preserving offsets), but keep also bar and repeat symbols
    abc = re.sub(r'(?m)%.*$', repl_by_spaces, abc)     # remove comments
    abc = re.sub(r'\[\w:.*?\]', repl_by_spaces, abc)   # remove embedded fields
    abc = re.sub(r'\\"', repl_by_spaces, abc)          # remove escaped " characters
    abc = re.sub(r'".*?"', repl_by_spaces, abc)        # remove strings
    abc = re.sub(r'\{.*?\}', repl_by_spaces, abc)      # remove grace notes
    abc = re.sub(r'!.+?!', repl_by_spaces, abc)        # remove ornaments like eg. !pralltriller!
    abc = re.sub(r'\+.+?\+', repl_by_spaces, abc)      # remove ornaments like eg. +pralltriller+
    return abc

def replace_chords_by_first_note(abc):
    # replace "[AD]2 [B2C2e2]" by "   A2       B2" - the first note in each chord, preserving offsets
    #abc = remove_non_note_fragments(abc)
    note_pattern = r"(?P<note>([_=^]?[A-Ga-gxz](,+|'+)?))(?P<length>\d{0,2}/\d{1,2}|/+|\d{0,2})(?P<broken>[><]?)"
    def sub_func(m):
        match1 = re.search(note_pattern, m.group(0))
        if match1:
            match_many = re.search('(' + note_pattern + '\-?)+', m.group(0))
            return ' ' * (len(match_many.group(0)) - len(match1.group(0)) + 2) + match1.group(0)
        else:
            return ' ' * len(match1.group(0))
    return re.sub(r'\[.*?\]', sub_func, abc)
	
def strip_abc(abc):
    abc = simplify_bars(abc)
    abc = remove_non_note_fragments(abc)
    abc = replace_chords_by_first_note(abc)
    return abc

def get_bar_length(abc, default_length, metre):
    #abc = remove_non_note_fragments(abc)
    #abc = replace_chords_by_first_note(abc)
    abc = strip_abc(abc)

    total_length = Fraction(0)
    last_broken_rythm = ''
    tuplet_notes_left = 0  # how many notes in the current tuplet are we yet to see
    tuplet_time = 2
    count = 0

    for match in re.finditer(r'(%s)|(%s)' % (note_pattern, tuplet_pattern), abc):
        n = match.group(0)
        if n[0] == '(':
            tuplet_notes = int(match.group('p'))
            tuplet_time = match.group('q')
            if tuplet_time:
                tuplet_time = int(tuplet_time)
            else:
                if tuplet_notes in [3, 6]:
                    tuplet_time = 2
                elif tuplet_notes in [2, 4, 8]:
                    tuplet_time = 3
                else: #elif tuplet_notes in [5, 7, 9]:
                    if metre.numerator % 3 == 0:
                        tuplet_time = 3 # for compound meter 6/8, 9/8, 12/8, etc
                    else:
                        tuplet_time = 2

            tuplet_notes_left = match.group('q')
            if tuplet_notes_left:
                tuplet_notes_left = int(tuplet_notes_left)
            else:
                tuplet_notes_left = tuplet_notes
            continue
        length = match.group('length')
        if default_length == DEFAULT_LENGTH:
            length = length.split('/')[0]  # ignore any fraction
            multiplier = Fraction(1, int(length))
            for dot in match.group('dot'):
                multiplier = multiplier * Fraction(3, 2)
            total_length = total_length + multiplier
        else:
            multiplier = Fraction(1)
            broken_rythm = match.group('broken')
            if broken_rythm == '>' or last_broken_rythm == '<':
                multiplier = Fraction(3, 2)
            elif broken_rythm == '<' or last_broken_rythm == '>':
                multiplier = Fraction(1, 2)
            last_broken_rythm = broken_rythm

            # 1.3.6.5 [JWDJ] 2015-12-19 divisor parsed similar to abcm2ps
            dividend = length.split('/')[0]
            if dividend:
                multiplier = multiplier * Fraction(int(dividend))

            for divmatch in re.finditer(r'/(\d*)', length):
                divisor = divmatch.group(1)
                if divisor:
                    divisor = int(divisor)
                else:
                    divisor = 2
                multiplier = multiplier / Fraction(divisor)

            if tuplet_notes_left:
                multiplier = multiplier * Fraction(tuplet_time, tuplet_notes)
                tuplet_notes_left -= 1
            total_length = total_length + multiplier * default_length
        count += 1
    return total_length


#
# End of EasyABC code
#

def find_phrase_end(music, stripped_music, note_end):
	end = note_end
	length = len(music)
	while end < length and " y|)]}-".find(stripped_music[end]) >= 0 and (music[end] != "[" or (end > length + 2 and music[end+2] == ":")):
		end += 1
	return end

def new_words_line(lineno, words, line_note_count, voice, split_option, recode_option):
	line = ("w:" if lineno == 0 or split_option else "+:")
	if recode_option:
		letter = ord("A") if voice == 0 else ord("a")
		n = 1
		for i in range(line_note_count):
			if i < len(words) and words[i] == "_":
				line += "_"
			else:
				if n > 1:
					line += " "
				line += chr(letter + lineno) + str(n)
				n += 1
	else:
		line += " ".join(words).replace(" _", "_")
	return line

def format_abc(lines, split_option, recode_option):
	if split_option is None:
		split_option = False
		music_lineno = 0
		for line in lines:
			if len(line) < 2 or line[0] == "%":
				continue
			if line[:2] == "V:":
				music_lineno = 0
			if line[1] != ":":
				music_lineno += 1
				if music_lineno >= 2:
					split_option = True
					break
	if recode_option is None:
		recode_option = False
		for line in lines:
			if line[:4].lower() == "w:a1":
				recode_option = True
				break
	lines.append("^:")
	meter = get_metre("")
	default_len = get_default_len("")
	new_lines = []
	voice = None
	words = []
	music = ""
	line_lengths = []
	for line in lines:
		if len(line) < 2 or line[0] == "%" or (line[1] == ":" and line[0] != "|" and (voice == None or (line[0] != "w" and line[0] != "+"))):
			#print(words)
			if len(music) > 0:
				if not split_option:
					new_lines.append(music)
				stripped_music = strip_abc(music)
				#print(str(len(music)) + " " + str(len(stripped_music)))
				#print(music)
				#print(stripped_music)
				notes_iter = re.finditer(r'(%s)|(%s)' % (note_pattern, tuplet_pattern), stripped_music)
				start = 0
				end = 0
				if voice == 0:
					for lineno in range(len(words)):
						note_count = 0
						while True:
							try:
								note = next(notes_iter)
								#print(note, end="")
								#print(" " + words[lineno][note_count])
								if "zx".find(note.group(0)[0]) < 0:
									note_count += 1
								if note_count == len(words[lineno]):
									if lineno == len(words) - 1:
										end = len(music)
									else:
										end = find_phrase_end(music, stripped_music, note.end())
									break;
							except:
								end = len(music)
								break
						if (split_option and end > start):
							new_lines.append(music[start:end] + ("\\" if (lineno+1) < len(words) else ""))
						new_lines.append(new_words_line(lineno, words[lineno], note_count, voice, split_option, recode_option))
						#print (new_lines[-1])
						line_lengths.append(get_bar_length(music[start:end], default_len, meter))
						start = end
					#print(line_lengths)
				else:
					lineno = 0
					line_len = 0
					line_note_count = 0
					note = next(notes_iter)
					while note is not None:
						next_note = None
						try:
							next_note = next(notes_iter)
						except:
							next_note = None
						line_len += get_bar_length(note.group(0), default_len, meter)
						if "zx".find(note.group(0).strip()[0]) < 0:
							line_note_count += 1
						#print(note, end="")
						#print(" " + str(line_len) + " " + str(line_note_count))
						if line_len >= line_lengths[lineno] or next_note is None:
							if next_note is None:
								end = len(music)
							else:
								end = find_phrase_end(music, stripped_music, note.end())
							if split_option:
								new_lines.append(music[start:end] + ("\\" if (lineno+1) < len(line_lengths) else ""))
								#print (new_lines[-1])
							if len(words) > 0:
								line_words = ([] if lineno >= len(words) else words[lineno])
								new_lines.append(new_words_line(lineno, line_words, line_note_count, voice, split_option, recode_option))
							start = end
							line_len -= line_lengths[lineno]
							line_note_count = 0
							lineno += 1
						note = next_note
				words = []
				music = ""
			if line != "^:":
				new_lines.append(line.strip())
		if len(line) < 2 or line[0] == "%" or line == "^:":
			continue
		if line[:2] == "M:":
			meter = get_metre(line)
		if line[:2] == "L:":
			default_len = get_default_len(line)
		if line[:2] == "V:":
			voice = (0 if voice == None else voice+1)
		if line[:2] == "w:" or (voice != None and line[:2] == "+:"):
			new_words = []
			tokens = re.split(r'( |_|-)', line[2:].strip())
			for token in tokens:
				if token == "-":
					new_words[-1] += token
				elif token != "" and token != " ":
					new_words.append(token)
			#if len(words) > 0:
			#	words[-1] = new_words
			#else:
			words.append(new_words)
		if line[1] != ":" or line[0] == "|":
			if voice == None:
				voice = 0
			eol = len(line.strip())
			if line[-1] == "\\":
				eol -= 1
			music += line[:eol]
			#if len(words) > 0:
			#	words.append([])
	return new_lines

if __name__ == "__main__":
	if len(sys.argv) > 1:
		split_option = None
		recode_option = None
		for i in range(1,len(sys.argv)):
			if sys.argv[i] == "-split" or sys.argv[i] == "-resplit":
				split_option = True
			if sys.argv[i] == "-join":
				split_option = False
			if sys.argv[i] == "-code" or sys.argv[i] == "-recode":
				recode_option = True
			if sys.argv[i] == "-keepwords":
				recode_option = False
		with open(sys.argv[-1], encoding=ENCODING) as f:
			lines = f.readlines()
		for line in format_abc(lines, split_option, recode_option):
			print(line)
	else:
		print("Syntax: " + sys.argv[0] + " [-split | -join] [-code | -keepwords] abc_file")
