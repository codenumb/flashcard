import tkinter as tk
from tkinter import messagebox,filedialog
from bs4 import BeautifulSoup
import requests
from tkhtmlview import HTMLScrolledText
import os
import sys
import json

def extract_element(soup,name:str,class_:str):
    data=None
    try:
        data = soup.find(name, class_=class_).get_text(strip=True)
    except:
        data = None
    return data

def get_word_definition(word):
    """Fetch and extract word definition from the LDOCE dictionary page."""
    url = f"https://www.ldoceonline.com/dictionary/{word}"
    
    try:
        # Send a GET request to the URL
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the div with class "dictionary" (where definitions are typically found)
            dictionary_div = soup.find('div', {'class': 'dictionary'})
            
            if dictionary_div:
                # Return the HTML content of the dictionary div
                return str(dictionary_div)
            else:
                return "Definition not found."
        else:
            return f"Failed to retrieve the page. Status code: {response.status_code}"
    except Exception as e:
        return f"Failed to retrieve the page. Error: {e}"

class FlashcardApp:
    def __init__(self):

        # List of words and their meanings
        self.words = []
        self.current_index = 0
        self.is_flipped = False
        self.definition_html = ""  # To store HTML content for the definition
        self.current_word = ''
        self.lines = []

        if getattr(sys, 'frozen', False):  # Running as a bundled app
            # If running as an exe, use sys._MEIPASS to get the correct path
            base_path = sys._MEIPASS            
        else:  # Running as a script
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.configFilePath = os.path.join(base_path, 'configs.json')
        self.configJson = self.loadConfigFile()
                
        #create GUI
        self.initGUI()

        if(self.verifySourceFile(self.configJson["word_src_path"])):
            self.wordSrcTkVar.set((self.configJson["word_src_path"]))

        #read word src file
        self.readWordSrcFile(self.configJson["word_src_path"])

        #load words into UI
        self.LoadList()

        print("done init")
        
    def initGUI(self):
        self.root = tk.Tk()
        self.root.title("Flashcard App")
        self.root.geometry("800x600")  # Initial size, will scale with window resizing
        self.wordSrcTkVar=tk.StringVar(value="browse a word source")
        self.newWord=tk.StringVar(value="")

        # Configure grid layout to only expand the "Word and Meaning" area
        self.root.grid_rowconfigure(0, weight=2)  # More space for word display
        self.root.grid_rowconfigure(1, weight=0)  # Buttons
        self.root.grid_rowconfigure(2, weight=0)  # src file

        # Column configurations:
        self.root.grid_columnconfigure(0, weight=0)  # Listbox column (no expansion)
        self.root.grid_columnconfigure(1, weight=0)  # Scrollbar column (no expansion)
        self.root.grid_columnconfigure(2, weight=2)  # Word and Meaning area (expands)

        # Word List Section (0,0) and (1,0)
        self.word_listbox = tk.Listbox(self.root, font=("Arial", 14), height=15)
        self.word_listbox.grid(row=0, column=0, rowspan=2, padx=5, pady=10, sticky="nsew")

        # Create a Scrollbar for the Listbox
        self.scrollbar = tk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.word_listbox.yview, width=15)
        self.scrollbar.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=10)  # Place scrollbar next to listbox

        # Link the Listbox with the scrollbar
        self.word_listbox.config(yscrollcommand=self.scrollbar.set)

        # Frame for add new word
        addWordFrame = tk.Frame(self.root)
        addWordFrame.grid(row=2,column=0,padx=5,pady=5,sticky='nsew')

        self.addWordEntry = tk.Entry(addWordFrame,textvariable=self.newWord,justify='left')
        self.addWordEntry.pack(side=tk.LEFT,padx=5)

        self.addWordButton = tk.Button(addWordFrame,text="Add",command=self.addNewWord)
        self.addWordButton.pack(padx=2)

        # Word and Meaning Display (0,2)
        self.card_text = HTMLScrolledText(self.root, html="")
        self.card_text.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # Frame for words text browser entry
        wordSrcFrame = tk.Frame(self.root)
        wordSrcFrame.grid(row=2,column=2,padx=5,pady=5,sticky='nsew')
        
        self.browseButton = tk.Button(wordSrcFrame,text="Browse",command=self.browse_src_file)
        self.browseButton.pack(side='left',padx=2,anchor=tk.CENTER) 
        
        self.srcLabel = tk.Label(wordSrcFrame,textvariable=self.wordSrcTkVar,justify='left',
                                 state='disabled', borderwidth=2, relief=tk.FLAT)
        self.srcLabel.pack(padx=2,side='left',anchor=tk.CENTER)

        #frame for buttons
        buttonFrame = tk.Frame(self.root)
        buttonFrame.grid(row=1, column=2, padx=50, pady=5, sticky="e")

        # Buttons for actions (1,1), (1,2), (1,3)
        self.rem_button = tk.Button(buttonFrame, text="remove", command=self.removeWord,state="disabled")
        self.rem_button.pack(side='left',padx=5)

        self.prev_button = tk.Button(buttonFrame, text="Previous", command=self.show_previous_word)
        self.prev_button.pack(side='left',padx=5)

        self.flip_button = tk.Button(buttonFrame, text="Flip", command=self.flip_card)
        self.flip_button.pack(side='left',padx=5)

        self.next_button = tk.Button(buttonFrame, text="Next", command=self.show_next_word)
        self.next_button.pack(side='left',padx=5)

        # Bind the Listbox selection event to update the flashcard
        self.word_listbox.bind('<<ListboxSelect>>', self.on_word_select)
        
    def convert_html_to_custom_format(self,html_content):
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        try:
            # Extract the related topics and format them
            related_topics = soup.find('span', class_='topics_container')
            related_text = extract_element(related_topics,'span', class_='related_topics')
            topic_text = extract_element(related_topics,'a', class_='topic')

            # Extract headword (HWD), hyphenation, pronunciation (PRON), part of speech (POS), and grammar (GRAM)
            hwd = extract_element(soup,'span', class_='HWD')
            hyphenation = extract_element(soup,'span', class_='HYPHENATION')
            pron = extract_element(soup,'span', class_='PRON')
            pos = extract_element(soup,'span', class_='POS')
            gram = extract_element(soup,'span', class_='GRAM')

            # Format the first paragraph
            paragraph = f'<p>{related_text}: {topic_text}<br />' \
                        f'<span style="color: #ff0000;"><strong>{hwd}</strong></span> {hyphenation} ' \
                        f'<span style="color: #ff6600;">/ {pron} /</span> ' \
                        f'<span style="color: #339966;"><strong> {pos}</strong></span> {gram}</p>'

            # Initialize the output string
            output_html = paragraph

            # Extract the senses and format them
            for sense in soup.find_all('span', class_='Sense'):
                # Extract the sense number, register label, activity, definition, related word, and examples
                sensenum = extract_element(sense,'span', class_='sensenum')
                
                # Check for REGISTERLAB (register label) and ACTIV (activity)
                registerlab = sense.find('span', class_='REGISTERLAB')
                registerlab = registerlab.get_text(strip=True) if registerlab else ''
                
                activ = sense.find('span', class_='ACTIV')
                activ = activ.get_text(strip=True) if activ else ''
                
                # Check for DEF span (definition)
                definition_span = sense.find('span', class_='DEF')
                definition = definition_span.get_text(strip=False) if definition_span else ''

                # Check for RELATEDWD (related word)
                relatedwd = sense.find('span', class_='RELATEDWD')
                relatedwd = relatedwd.get_text(strip=True) if relatedwd else ''
                
                # Check for EXAMPLE (example sentence)
                example = sense.find('span', class_='EXAMPLE')
                example = example.get_text(strip=False) if example else ''

                # Extract additional examples from GramExa
                additional_examples = []
                gram_exa = sense.find_all('span', class_='GramExa')
                for exa in gram_exa:
                    additional_example = exa.find('span', class_='EXAMPLE')
                    if additional_example:
                        additional_examples.append(additional_example.get_text(strip=True))

                # Format each sense item as a <p> tag
                sense_content = f'<p>{sensenum}. '
                
                # Add register label and activity
                if registerlab:
                    sense_content += f'<span style="color: #333399;"><em>{registerlab}</em></span> '
                if activ:
                    sense_content += f'<span style="color: #333399;"><em>{activ}</em></span> '
                
                sense_content += f'{definition} {relatedwd}<br />'

                # Add the main example
                if example:
                    sense_content += f'<span style="color: #808080;"><em>&nbsp;&nbsp;{example}</em></span><br />'

                # Add additional examples with indentation
                for ex in additional_examples:
                    sense_content += f'<span style="color: #808080;"><em>&nbsp;&nbsp;{ex}</em></span><br />'

                # Close the <p> tag for the sense item
                sense_content += '</p>'

                # Add this sense content to the final output
                output_html += sense_content
        except Exception as e:
            output_html = f"{e}"
        # Return the final HTML output
        return output_html

    def loadConfigFile(self):
        with open(self.configFilePath,mode="r+") as configFile:
            try:
                self.configJson = json.load(configFile)
            except Exception as e:
                self.configJson={}
            finally:
                return self.configJson
        
    def addToWordFile(self,word): 
        self.lines.append(word)
        with open(self.configJson['word_src_path'], "w") as srcFile:
            srcFile.writelines(self.lines)

    def removeFromWordFile(self,word,index):
        if(word in self.lines[index]):
                self.lines.pop(index)
        with open(self.configJson['word_src_path'], "w") as srcFile:
            srcFile.writelines(self.lines)

    def addNewWord(self):
        word=self.addWordEntry.get()
        self.addToWordFile(f'{word}\n')
        self.readWordSrcFile(self.configJson['word_src_path'])
        self.LoadList()
    
    def removeWord(self):
        remWord,_=self.words[self.current_index]
        for word,_ in self.words:
            if(word == remWord):
                self.removeFromWordFile(word,self.current_index)
                self.readWordSrcFile(self.configJson['word_src_path'])
                self.LoadList()
                self.rem_button.configure(state="disabled")
                break

    def write_config_file(self,configs:dict):
        with open(self.configFilePath,"r+") as configFile:
            json.dump(configs,configFile)

    def verifySourceFile(self,path):
        status = False
        try:
            status=os.path.exists(path)
        except Exception as e:
            messagebox.showerror("Error","unable to find word list")
        finally:
            return status

    def get_word_def(self,word):
        def_raw=self.get_word_meaning(word)
        formatted_def = self.convert_html_to_custom_format(def_raw)
        return formatted_def
    
    def get_word_meaning(self,word):
        """
        This function takes a URL to a Longman Dictionary of Contemporary English page,
        parses the page, and returns the meaning of the word in HTML format.
        """
        url = f"https://www.ldoceonline.com/dictionary/{word}"
        # Send a GET request to the URL
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url,headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the page content with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the element with the 'ldoceEntry' class (which contains the word's meaning)
            entry = soup.find(class_='ldoceEntry')

            if entry:
                # Extract the meaning and format as HTML
                return entry.prettify()  # This will give you the HTML formatted string
            else:
                return "Meaning not found."
        else:
            return f"Failed to retrieve the page. Status code: {response.status_code}"

    def browse_src_file(self):
        path = filedialog.askopenfilename(
            title="Select a word source file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
        if(not path):
            return
        if(not self.verifySourceFile(path)):
            return
        self.wordSrcTkVar.set(path)

        self.configJson['word_src_path']=path

        #read word src file
        self.readWordSrcFile(self.configJson["word_src_path"])

        #load words into UI
        self.LoadList()

        #write src file path to config file
        self.write_config_file(self.configJson)

        print(self.wordSrcTkVar)
    
    def update_card(self):
        """Update the card with the current word or meaning."""
        word, meaning = self.words[self.current_index]
        self.definition_html = self.get_word_def(word)
        self.card_text.delete(1.0, tk.END)  # Clear previous content
        if self.is_flipped:
            # print(self.definition_html)
            self.card_text.set_html(self.definition_html)
        else:
            self.card_text.set_html( word)

    def flip_card(self):
        """Flip the card to show the meaning or the word."""
        self.is_flipped = not self.is_flipped
        if self.is_flipped:
            # Fetch the word definition only when flipping
            self.definition_html = get_word_definition(self.current_word)
        self.update_card()

    def show_next_word(self):
        """Show the next word in the list."""
        if self.current_index < len(self.words) - 1:
            self.current_index += 1
            self.is_flipped = False
            self.current_word = self.words[self.current_index][0]
            self.definition_html = ""  # Reset the definition
            self.update_card()
        else:
            messagebox.showinfo("End of List", "You have reached the end of the list.")

    def show_previous_word(self):
        """Show the previous word in the list."""
        if self.current_index > 0:
            self.current_index -= 1
            self.is_flipped = False
            self.current_word = self.words[self.current_index][0]  # Update the current word
            self.definition_html = ""  # Reset the definition
            self.update_card()
        else:
            messagebox.showinfo("Start of List", "You are at the beginning of the list.")

    def on_word_select(self, event):
        """Called when the user selects a word from the Listbox."""
        # Get the index of the selected word
        selected_index = self.word_listbox.curselection()
        if selected_index:
            # Get the word and its meaning from the list of words
            self.current_index = selected_index[0]
            self.is_flipped = True
            self.update_card()
            self.rem_button.configure(state="active")
    
    def LoadList(self):
        i = 1
        self.word_listbox.delete(0,tk.END)
        for word, _ in self.words:
            self.word_listbox.insert(tk.END, f"{i}. {word}")
            i = i + 1
        print("done loading")

    def readWordSrcFile(self,file_name):
        """Load words and their meanings from a file."""

        #check if file path is correct
        if(not self.verifySourceFile(file_name)):
            return

        with open(file_name, "r") as file:
            self.lines = file.readlines()

        words = []
        try:
            with open(file_name, "r") as file:
                for index,line in enumerate(file):
                    if(line == '\n'):
                        self.lines.pop(index)
                    if " - " in line:
                        word, meaning = line.strip().split(" - ", 1)
                        words.append((word, meaning))
                    else:
                        word= line.strip()
                        meaning=""
                        words.append((word,meaning))
        except FileNotFoundError:
            messagebox.showerror("File Not Found", f"The file {file_name} was not found!.")
        except Exception as e:
            messagebox.showerror("Error",f"unable to load {file_name}: {e} ")
        self.words = words

if __name__ == "__main__":

    # Determine if we are running as a PyInstaller bundle
    # if getattr(sys, 'frozen', False):  # Running as a bundled app
    #     # If running as an exe, use sys._MEIPASS to get the correct path
    #     base_path = sys._MEIPASS
    # else:  # Running as a script
    #     base_path = os.path.dirname(os.path.abspath(__file__))

    # Load words from the text file
    # file_path = os.path.join(base_path, 'words.txt')
    # words = load_words(file_path)
    # if words:
    #     # Create the main application window
    #     root = tk.Tk()
    #     app = FlashcardApp(root)
    #     # app.update_card()
    #     # app.LoadList(word=words)
    #     root.mainloop()
    # else:
    #     print("No words to display.")
    app = FlashcardApp()
    app.root.mainloop()