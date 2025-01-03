import PyInstaller.__main__

PyInstaller.__main__.run(
    [
        'flashcard.py',
        '--windowed',
        '--noconsole',
        '--icon=flash-card.ico',
        '--add-data=words.txt:.'
    ]
)