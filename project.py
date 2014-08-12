#!/usr/bin/python
#-*- coding: utf-8 -*-
import Tkinter as tk
from PIL import Image, ImageTk
import random, json, sys
import urllib2, urllib
from xml.dom.minidom import parseString
import pygame


""" Om spelprojektet:
        
    Spelet går ut på att visa bilder på kända personer, händelser och scener ur filmer, och att användaren
    ska kunna svara på vad bilden förställer. Från början syns endast en liten del av bilden genom att den 
    täcks med svarta rutor. När man klickar på en av rutorna visas den del av bilden under rutan. Sammanlagt 
    5x5=25 rutor. 

    Ju färre rutor man behöver klicka bort innan man kommit på vad bilden föreställer, ju fler poäng får man.

    Förutom bilder används även text-citat från kända personer. Då går det ut på att svara vem citatet tillhör.

    Spelet går även på tid. Man har 20 sekunder på sig att svara på varje fråga.
    Svarar man fel får man fortsätta att svara tills tiden gått ut, men för varje felsvar minskar mängden 
    poäng man kan få för ett korrekt svar.

    Alla bilder, frågor, och citat läses in via en JSON-fil. 
    Sätts konstanten "QUOTE_API_RANGE" till ett värde, t ex 5, kommer även fem externa citat läsas in från ett 
    webb-API genom metoden "get_quote_data". Dessa citat läggs till i den befintliga listan (self.data) som 
    innehåller datan för spelet. Denna lista ändrar sorteringsordning för varje gång ett nytt spel påbörjas, 
    så att frågorna inte ska komma i samma ordning.

    Många variabler används mellan metoderna och har därför gjorts till instansvariabler.

    Bilden som täcks av svarta rutor i funktionen "create_grid", täcks egentligen inte, utan den ritas upp 
    först när man klickar på rutorna. 
    Varje ruta är en Tkinter-Canvas, och när den klickas på ritas den del av bilden upp som stämmer överrens med 
    positionen för rutans plats i x- och y-led genom for-loopen i funktionen "show_more". 

    High-score:en fungerar som så att, först kontrolleras on namnet på spelaren finns i high-score-listan redan:
    Finns inte personen läggs den till. Finns personen; kontrolleras om personens nya poäng är högre än den 
    tidigare poängen. Är den högre ersätter den det gamla resultatet, annars görs ingenting.

    Klickar man på knappen "Avbryt spel", avbryts pågående spel och man tas till high-score-listan. Annars 
    fortsätter spelet så länge det finns speldata, för att sedan automatiskt tas till high-score-listan.


    Gjord av: Per Magnusson

    Python: 2.7.2
    OS: OS X 10.8.4
    
"""

class Project:

    # constants
    GAME_TYPE_PHOTO = 1  # never change!
    GAME_TYPE_QUOTE = 2  # never change!
    POINTS = 100  # nr of ponts per correct answer
    TIME_LIMIT = 20  # seconds per question
    QUOTE_API_RANGE = 0  # nr of quotes fetched from web API
    FILE_HIGH_SCORE = 'highscore.txt'  # text file to store high scores

    def __init__(self):
        #
        self.data = None  # all game data
        self.timer = 0  # timer for questions
        self.data_length = 0
        self.data_current_nr = 0  # current iterated index on shuffled list
        self.block_clicked_count = 0
        self.question_text = ''
        self.answer_text = ''
        self.photo_canvas = None
        self.quote_label = None
        self.game_type = 0
        self.after_id = None
        self.answer_try_count = 0
        self.total_won = 0
        self.high_score_frame = None
        self.root = None
        self.frame = None
        self.user_name_string = ''
        
        # pygame mixer init
        pygame.mixer.init(44100, -16, 2, 1024)
        self.sound_correct = pygame.mixer.Sound('correct.ogg')
        self.sound_wrong = pygame.mixer.Sound('wrong.ogg')
        self.sound_time = pygame.mixer.Sound('time.ogg')
        #
        self.main()




    def main(self):
        if not self.root:
            self.root = tk.Tk()
            self.root.title('Vem-Vad-När!')
            self.root.minsize(650, 750)
            self.root.maxsize(650, 750)
        
        if self.frame:
            self.frame.destroy()
        self.frame = tk.Frame(self.root, padx=10, pady=10)
        self.frame.pack(fill=tk.BOTH, expand=tk.YES, padx=10, pady=10)
            
        # inner frame for game content
        self.frame_inner = tk.Frame(self.frame)
        self.frame_inner.pack()

        # header
        self.header_label = tk.Label(self.frame_inner, text='', font=('Helvetica', 30))
        self.header_label.pack()

        self.user_name()

        # run loop
        self.root.mainloop()



    def game_plan(self):
        # answer status label
        self.answer_status_label = tk.Label(self.frame)
        self.answer_status_label.pack()

        # countdown timer
        self.countdown_label = tk.Label(self.frame)
        self.countdown_label.pack()

        self.answer_wrap_frame = tk.Frame(self.frame)
        self.answer_wrap_frame.pack()

        # points label
        self.points_label = tk.Label(self.frame)
        # input answer
        self.answer_entry = tk.Entry(self.answer_wrap_frame)
        # answer label
        answer_info_label = tk.Label(self.answer_wrap_frame, text='Svar:')
        # answer button
        self.answer_button = tk.Button(self.answer_wrap_frame, text="Svara", command=self.do_answer)

        # init new game
        self.new_game()

        # answer info label pack
        answer_info_label.pack(side=tk.LEFT)
        # input answer pack
        self.answer_entry.pack(side=tk.LEFT, expand=tk.YES, fill=tk.X)
        self.answer_entry.focus()
        
        # points label pack
        self.points_label.pack()

        # answer button pack
        self.answer_button.pack(side=tk.LEFT)

        # finish game
        self.finish_game_button = tk.Button(self.frame, text='Avbryt spel >>', command=self.display_high_score)
        self.finish_game_button.pack(side=tk.RIGHT)
        # play again button
        self.play_again_button = tk.Button(self.frame, text='Starta om', command=self.main)
        self.play_again_button.pack(side=tk.LEFT)
        # quit game
        tk.Button(self.frame, text='Avsluta', command=self.root.destroy).pack(side=tk.LEFT)



    def user_name(self):  # display welcome screen to get username.
        self.root.configure(bg='#678de3')
        self.user_name_frame = tk.Frame(self.frame)
        self.user_name_frame.pack()
        tk.Label(self.user_name_frame, text='Välkommen till Vem-Vad-När!', fg='#2a395b', font=('Verdana', 21, 'bold')).pack()
        info = """
Spelet går ut på att samla så mycket poäng som möjligt. 
Poäng får du när du anger rätt svar på den fråga som ställs.
(Fyndigt va?)
För att kunna svara på en bildfråga kommer du behöva klicka
bort en del av de svarta rutorna som täcker bilden. Ju färre
rutor du klickar bort, dessto fler poäng får du, om du lyckas
svara rätt på frågan det vill säga. Du får några försök på dig
att svara rätt, men tänkt på att ju fler gånger du försöker
dessto mindre poäng får du!

Ja just det ja, det går på tid också så det är bäst du skyndar dig!
        """
        tk.Label(self.user_name_frame, text=info, font=('Verdana', 16)).pack()
        tk.Label(self.user_name_frame, text='Ange ditt namn:').pack()
        self.user_name_entry = tk.Entry(self.user_name_frame)
        self.user_name_entry.focus()
        self.user_name_entry.insert(0, self.user_name_string)
        self.user_name_entry.pack()
        button = tk.Button(self.user_name_frame, text='OK, nu spelar vi!', command=self.get_user_name)
        button.pack()



    def get_user_name(self):  # set username to variabler from input
        self.user_name_string = self.user_name_entry.get()[0:10]
        if self.user_name_string:
            self.user_name_frame.destroy()
            self.game_plan()
        else:
            self.main()



    def new_game(self):
        # reset values
        self.answer_try_count = 0
        self.total_won = 0
        self.data_current_nr = 0 
        self.points_label.configure(text='Du har 0 poäng.'.format(self.total_won))
        self.answer_button.configure(state=tk.NORMAL)

        if not self.answer_wrap_frame:
            self.answer_wrap_frame.pack()

        # collect data from json
        self.data = self.get_data()
        # get nr of data items
        self.data_length = len(self.data)
        
        # cancel after-function
        if self.after_id:
            self.root.after_cancel(self.after_id)

        # remove frame
        if self.high_score_frame:
            self.high_score_frame.destroy()

        # init game plan
        self.generate_game_plan()



    def generate_game_plan(self):
        # reset values
        self.block_clicked_count = 0
        self.answer_try_count = 0
        self.answer_status_label.configure(text='')
        self.countdown_label.configure(text='')
        self.answer_entry.delete(0, tk.END)  # clear entry field

        # del old canvas/label
        if self.photo_canvas:
            self.photo_canvas.destroy()
        if self.quote_label:
            self.quote_label.destroy()

        # data item to display    
        item_nr = self.pick_new_data_item()
        if item_nr:
            # photo game:
            if self.data[item_nr]['type'] == self.GAME_TYPE_PHOTO:
                self.game_type = self.GAME_TYPE_PHOTO
                # create canvas
                self.create_photo_canvas(item_nr)
                # create black block grid
                self.create_grid()
                self.show_init_img_block()

            # quote game:
            elif self.data[item_nr]['type'] == self.GAME_TYPE_QUOTE:
                self.game_type = self.GAME_TYPE_QUOTE
                self.create_quote_label(item_nr)
        
            # start timer 
            self.after_id = self.root.after(1000, lambda:self.countdown_timer(self.TIME_LIMIT))

        else:
            self.display_high_score()



    def get_data(self):
        try:
            json_data = open('data.json')
            data = json.load(json_data)
            json_data.close()
        except IOError:
            sys.stderr.write('Fel inträffade när datan skulle hämtas.\n')
            sys.exit(1)

        for r in data:
            if r['type'] == self.GAME_TYPE_PHOTO:
                r['image'] = ImageTk.PhotoImage(Image.open(r['image']))

        # append quotes from web api
        for x in range(self.QUOTE_API_RANGE):
            quote_data = self.get_quote_data()  # return as tuple
            if quote_data:
                data.append({"type": 2, "question": 'Vem sa?', "quote": quote_data[0], "answer": quote_data[1]})

        random.shuffle(data)  # shuffle data
        return data


    
    def pick_new_data_item(self):
        if self.data_current_nr >= self.data_length-1:
            return False
        else:
            self.data_current_nr += 1
            return self.data_current_nr


        
    def create_photo_canvas(self, item_nr):  # photo game canvas
        data = self.data[item_nr]
        self.question_text = data['question']
        self.answer_text = data['answer']
        self.back_image = data['image']
        self.header_label.configure(text=self.question_text)
        # canvas for main image
        self.photo_canvas = tk.Canvas(self.frame_inner, width=500, height=500)
        self.photo_canvas.pack(fill=tk.BOTH, expand=tk.YES)



    def create_quote_label(self, item_nr):  # quote game label
        data = self.data[item_nr]
        self.question_text = data['question']
        self.answer_text = data['answer']
        self.quote = '"{0}"'.format(data['quote'])
        self.header_label.configure(text=self.question_text)

        self.quote_label = tk.Label(self.frame_inner, width=310, height=20, wraplength=300,
                                    font=('Arial', 21))
        self.quote_label.pack()
        self.quote_label.configure(text=self.quote)



    def create_grid(self):  # grid with blac blocks for photo game
        self.block_list = []
        # black image
        self.black_block_img = ImageTk.PhotoImage(Image.open('black.png'))
        row = 0
        column = 0
        for x in range(25):  # 25 squared. create 5x5 pattern.
            column += 1
            if column > 5:
                column = 1
                row +=1
            self.block_list.append(tk.Canvas(self.photo_canvas, width=100, height=100))
            create_img = self.block_list[x].create_image(0, 0, image=self.black_block_img)
            self.block_list[x].grid(row=row, column=column)
            # add click handler (must be added in function to keep index value, otherwise last index value on all)
            self.add_click_handler(self.block_list, x, create_img)
        


    def add_click_handler(self, block_list, index, create_img):  # add click handler to black square blocks
        block_list[index].tag_bind(create_img, '<ButtonPress-1>', lambda a:self.on_click(index))



    def show_init_img_block(self):  # shows ONE random photo block on init photo game
        index = random.randint(0, 24)
        self.show_more(index)



    def on_click(self, index):  # click on photo game black block square
        self.show_more(index)  # show photo under black block square
        self.block_clicked_count += 1  # one more click

    

    def show_more(self, index):  # add photo part under clicked black block square
        x = 3
        y = 3
        for i in range(25):  # 25 squared. create 5x5 pattern.
            if index == i or index == None:
                self.block_list[i].create_image(x, y, image=self.back_image, anchor=tk.NW)
            x -= 100
            if x < -400:
                x = 3
                y -= 100

    

    def countdown_timer(self, seconds=None):  # show countdown timer
        if seconds:
            self.timer = int(seconds)
        if self.timer < 1:
            self.timer = 0
            self.sound_time.play()
            self.answer_button.configure(state=tk.DISABLED)
            self.countdown_label.configure(text='Tyvärr. Tiden är ute!')
            self.after_id = self.root.after(2000, self.next_question)
            return False
        else:
            try:
                self.countdown_label.configure(text='{0} sekunder kvar.'.format(self.timer))
            except:
                return False

        self.timer -= 1
        self.after_id = self.root.after(1000, self.countdown_timer)  # delay 1 second




    def do_answer(self):  # clicked answer button
        if self.answer_entry.get().lower() == self.answer_text.lower():  # answer is correct
            if self.game_type == self.GAME_TYPE_PHOTO:
                self.show_more(None)  # remove all square blocks

            points = self.calculate_points()
            self.sound_correct.play()
            self.answer_button.configure(state=tk.DISABLED)
            self.total_won += points
            self.points_label.configure(text='Du har {0} poäng.'.format(self.total_won))
            self.answer_status_label.configure(text='Rätt svarat!', fg='#006c00', font=('Helvetica', 16))
            self.root.after_cancel(self.after_id)  # cancel after() func recursion in countdown_timer()
            self.countdown_label.configure(text='')
            self.after_id = self.root.after(1500, self.next_question)
        else:
            self.sound_wrong.play()
            self.answer_try_count += 1
            self.answer_status_label.configure(text='Fel svarat.', fg='red', font=('Helvetica', 16))



    def next_question(self):  # step to next question
        self.answer_button.configure(state=tk.NORMAL)
        self.generate_game_plan()  # new game plan



    def calculate_points(self):
        total = 0
        points = self.POINTS
        if self.game_type == self.GAME_TYPE_PHOTO:
            decrease_clicked = self.block_clicked_count * 3  # decrease points for each clicked square block
            decrease_aswered = self.answer_try_count * 20  # decrease by try count (nr of wrong tries)
            total = points - decrease_clicked - decrease_aswered
            if total <= 10:  # mini points on correct
                total = 10

        elif self.game_type == self.GAME_TYPE_QUOTE:
            decrease = self.answer_try_count * 20
            if self.answer_try_count > 4:
                decrease = 90  # mini 10 points on correct
            total = points - decrease

        return total



    def display_high_score(self):  # high score results on cancel game button or end game
        # remove/configure prev widgets
        if self.after_id:
            self.root.after_cancel(self.after_id)
        if self.photo_canvas:
            self.photo_canvas.destroy()
        if self.quote_label:
            self.quote_label.destroy()
        self.finish_game_button.destroy()
        self.answer_wrap_frame.destroy()
        self.countdown_label.destroy()
        self.answer_status_label.destroy()
        self.points_label.configure(text='Du fick ihop {0} poäng.'.format(self.total_won))

        # add user to high score
        self.add_high_score(self.user_name_string, self.total_won)
        self.header_label.configure(text='High Score')
        high_score_dict = self.load_high_score()
        # sort list, highest first.
        high_score_list_sorted = sorted(high_score_dict.items(), key=lambda x: x[1], reverse=True)

        self.high_score_frame = tk.Frame(self.frame_inner)
        self.high_score_frame.pack()

        # high score list label
        tk.Label(self.high_score_frame, text='Namn \t Poäng \n', font=('Verdana', 16, 'bold')).pack()

        # output high score from sorted list to Label
        result = ''
        i = 0
        for item in high_score_list_sorted[0:10]:
            i += 1
            result += '{0}. {1} - {2}\n'.format(i, item[0], item[1])
        score_text = tk.Label(self.high_score_frame, text=result, font=('Verdana', 14), justify=tk.LEFT)
        score_text.pack()



    def add_high_score(self, name, points):  # add new data to high score text file
        high_score_dict = self.load_high_score()  # get current high score results from file
        update_old = False
        for key, value in high_score_dict.iteritems():  # dict with high scores: "Olle": 123 (name: points)
            if name == key:  # name exists already.
                if points > int(value):  # new result is higher than prev, - update.
                    update_old = True
                    high_score_dict[key] = points  # update prev result with new
                else:
                    # no update needed.
                    return False
                break

        # name not in list, add new.
        if not update_old:
            high_score_dict[name] = points  # add new name and result to dict

        # write to file from updated dict
        try:
            with open(self.FILE_HIGH_SCORE, 'w') as f:
                for key, value in high_score_dict.iteritems():
                    f.write('{0}\t{1}\n'.format(key, value))
        except IOError:
            sys.stderr.write('Kunde inte lägga till high score.\n')
            return False



    def load_high_score(self):  # load high score from text file
        high_score_dict = {}  # load to dict
        f = open(self.FILE_HIGH_SCORE, 'r')
        for line in f.readlines():
            line_elem = line.split('\t')
            high_score_dict[line_elem[0]] = int(line_elem[1].strip('\n'))
        f.close()
        return high_score_dict



    def get_quote_data(self):  # return as tuple
        # get xml feed
        try:
            xml_feed = urllib2.urlopen('http://www.stands4.com/services/v2/quotes.php?uid=2543&tokenid=Xor0DOW0C4Ag1Iay&searchtype=RANDOM')
            data = xml_feed.read()
            xml_feed.close()
            # parse content
            dom = parseString(data)
            # get quote and author string and return as list
            quote_string = [elem.childNodes[0].nodeValue for elem in dom.getElementsByTagName('quote')][0]
            author_string = [elem.childNodes[0].nodeValue for elem in dom.getElementsByTagName('author')][0]
            return quote_string, author_string
        except:
            return False



project = Project()
