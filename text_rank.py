import itertools, nltk, string
import gensim
from itertools import takewhile, tee, izip
import networkx
import collections, math,re
from textract import process as pdf2txt
import bs4,io,re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
from gensim.summarization import summarize,keywords
#import spacy
from nltk import word_tokenize, pos_tag, ne_chunk
import nltk.tag.stanford as st
import urllib
import urllib2
from bs4 import BeautifulSoup


def extract_candidate_words(text, good_tags=set(['JJ','JJR','JJS','NN','NNP','NNS','NNPS'])):
	# exclude candidates that are stop words or entirely punctuation
	punct = set(string.punctuation)
	stop_words = set(nltk.corpus.stopwords.words('english'))
	# tokenize and POS-tag words
	tagged_words = itertools.chain.from_iterable(nltk.pos_tag_sents(nltk.word_tokenize(sent) for sent in nltk.sent_tokenize(text)))
	# filter on certain POS tags and lowercase all words
	candidates = [word.lower() for word, tag in tagged_words if tag in good_tags and word.lower() not in stop_words and not all(char in punct for char in word)]
	return candidates

#TEXT_RANK
def score_keyphrases_by_textrank(text, n_keywords=0.05):
	# tokenize for all words, and extract *candidate* words
	words = [word.lower() for sent in nltk.sent_tokenize(text) for word in nltk.word_tokenize(sent)]
	candidates = extract_candidate_words(text)
	# build graph, each node is a unique candidate
	graph = networkx.Graph()
	graph.add_nodes_from(set(candidates))
	# iterate over word-pairs, add unweighted edges into graph
	def pairwise(iterable):
		"""s -> (s0,s1), (s1,s2), (s2, s3), ..."""
		a, b = tee(iterable)
		next(b, None)
		return izip(a, b)
	for w1, w2 in pairwise(candidates):
		if w2:
			graph.add_edge(*sorted([w1, w2]))
	# score nodes using default pagerank algorithm, sort by score, keep top n_keywords
	ranks = networkx.pagerank(graph)
	if 0 < n_keywords < 1:
		n_keywords = int(round(len(candidates) * n_keywords))
	word_ranks = {word_rank[0]: word_rank[1] for word_rank in sorted(ranks.iteritems(), key=lambda x: x[1], reverse=True)[:n_keywords]}
	keywords = set(word_ranks.keys())
	# merge keywords into keyphrases
	keyphrases = {}
	j = 0
	for i, word in enumerate(words):
		if i < j:
			continue
		if word in keywords:
			kp_words = list(takewhile(lambda x: x in keywords, words[i:i+10]))
			avg_pagerank = sum(word_ranks[w] for w in kp_words) / float(len(kp_words))
			keyphrases[' '.join(kp_words)] = avg_pagerank
			# counter as hackish way to ensure merged keyphrases are non-overlapping
			j = i + len(kp_words)
	
	return sorted(keyphrases.iteritems(), key=lambda x: x[1], reverse=True)

def getPDFContent(file):
	content = re.sub(r'[%s]' % ''.join(map(unichr, range(32) + range(127, 256))), '', pdf2txt(file)), pdf2txt(file) #Needed as it gives structured data
	#print content
	return content

def get_sections(file, group_by=4, chap_num=1, start_chap=2):
	s = ""
	f = open(file)
	for line in f:
		line = line.strip()
		if line.startswith("%d.%d" % (chap_num, start_chap)):
			s = line[len("%d.%d" % (chap_num, start_chap)):]
			break
	else:
		f.close()
		raise StopIteration
	i = start_chap + 1
	for line in f:
		line = line.strip()
		if line.startswith("%d.%d" % (chap_num, i)):
			if (i - start_chap) % group_by == 0:
				yield s
				s = ""
			s += (' ' if s else '') + line[len("%d.%d" % (chap_num, i)):]
			i += 1
		else:
			s += ' ' + line
	yield s
	f.close()

def scraper(text):
	driver = webdriver.Chrome()
	driver.get('http://textsummarization.net/text-summarizer')
	driver.find_element_by_xpath('//*[@id="text"]').send_keys(text)
	driver.find_element_by_xpath('//*[@id="sentnum"]').send_keys('15')
	driver.find_element_by_xpath('/html/body/div[4]/div[1]/div/div/div/form/table/tbody/tr[2]/td[1]/input').click()
	time.sleep(4)
	summarized_text = driver.find_element_by_xpath('/html/body/div[4]/div[1]/div/div[2]/p').text
	return summarized_text

def get_youtube_links(query):
	links = []
	query = urllib.quote(query)
	url = "https://www.youtube.com/results?search_query=" + query
	response = urllib2.urlopen(url)
	html = response.read()
	soup = BeautifulSoup(html,'lxml')
	for vid in soup.findAll(attrs={'class':'yt-uix-tile-link'}):
		links.append('https://www.youtube.com' + vid['href'])

	return links[0]


def main(filename):
	pdf_content = getPDFContent(filename+'.pdf')
	summy = summarize(pdf_content[1],0.05)
	text = re.sub(r'[%s]' % ''.join(map(unichr, range(32) + range(127, 256))), '', pdf_content[1])

	tagger = st.StanfordNERTagger('/home/cgh/PDFile/stanford-ner-2014-06-16/classifiers/english.all.3class.distsim.crf.ser.gz','/usr/share/stanford-ner/stanford-ner.jar')
	tag_results = tagger.tag(text.split())

	names = []
	for i in tag_results:
		try:
			if i[1] == 'PERSON':
				names.append(i[0])
		except:
			pass		

	with open(filename+'_structured.txt','w') as f:
		f.write(pdf_content[1])

	total_rank = []
	for section in get_sections(filename+'_structured.txt'):		
		sec = re.sub(r'[%s]' % ''.join(map(unichr, range(32) + range(127, 256))), '', section)
		sec_rank_list = score_keyphrases_by_textrank(sec)
		total_rank.append(sec_rank_list[:8])

	words=[]
	if total_rank ==[]:
		sec = re.sub(r'[%s]' % ''.join(map(unichr, range(32) + range(127, 256))), '', pdf_content[1])
		sec_rank_list = score_keyphrases_by_textrank(sec)
		total_rank = sec_rank_list[:15]

		for ranks in total_rank:
			words.append(ranks[0])
	else:	
		for ranks in total_rank:
			for i in ranks[:3]:
				words.append(i[0])

	#words.pop(0)
	words = list(set(words))
	ytlinks = []
	print words	
	w_1 = words[:len(words)/2]
	w_2 = words[len(words)/2+1]
	
	ytlinks.append(get_youtube_links(str(w_1).strip('[]')))
	ytlinks.append(get_youtube_links(str(w_2).strip('[]')))

	return total_rank,summy,names,ytlinks

#main('ai')


