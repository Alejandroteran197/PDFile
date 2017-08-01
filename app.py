#!/usr/bin/env python3
from flask import Flask, render_template, jsonify, request
from random import randint
from text_rank import*
from werkzeug.utils import secure_filename

app = Flask(__name__)



@app.route('/')
def home():
    return render_template('index.html')
    
@app.route('/pdfile', methods=['POST'])
def PDFile():
    file = request.files['pdfile']
    file.save(secure_filename('Chapter1.pdf'))
    key_words,summary,names,ytlinks = main('Chapter1')


    links = {}
    ids = list(youtube.keys())
    n = randint(0, len(ids) - 1)
    for _ in range(n):
        video_id = ids.pop(randint(0, len(ids) - 1))
        links[video_id] = youtube[video_id]

    selected_video = ytlinks[0]
    links['video_id'] = selected_video[selected_video.find('=')+1:]
    links['vid1'] = ytlinks[0].split('v=')[-1]
    links['vid2'] = ytlinks[1].split('v=')[-1]

    links['summary'] = summary
    links['key_words'] = key_words
    links['names'] = names
    links['ytlinks'] = ytlinks
    print(links)
    return jsonify(links)
    
if __name__ == '__main__':
    app.run()
