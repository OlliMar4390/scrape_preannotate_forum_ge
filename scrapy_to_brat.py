import json
import os
import re
from collections import defaultdict

import plac
from bs4 import BeautifulSoup

# /mnt/e/Studium/Weiterbildungen/Python/Portfolio/dfki_webscraping-master$ python scrapy_to_brat.py -n -d
# https://www.crummy.com/software/BeautifulSoup/bs4/doc/#contents-and-children

# these tags stand for paragraphs in the text, so newline before and after the text here
BLOCK_TAGS = ['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'blockquote']


# create statistics to see what the data offers to analyse *****************************************************

def show_statistics(dicthreads):
    dicthread_stats = {}
    POST_COUNT = 'Post count'
    USERS_COUNT = 'Users count'
    THREADS_WITH = 'Threads with'

    for sthread_name, dicthread in dicthreads.items():

        dicthread_stats[sthread_name] = {}

        # number of posts in a thread
        dicthread_stats[sthread_name][POST_COUNT] = len(dicthread)

        # number of users in a thread
        dicthread_stats[sthread_name][USERS_COUNT] = len(set(
            [dicposts['username'] for dicposts in dicthread]
            ))

    # print statistics
    print('Total threads: %s' % len(dicthread_stats))
    
    def stats(description='', count_what='', accumulate=None, comp_lambda=None, measurement=''):
        print(
            '%s: %s%s' % (
                description,
                accumulate([postcount[count_what] for postcount in dicthread_stats.values()
                            if comp_lambda(postcount[count_what])]),
                measurement
                )
            )
            
    stats(THREADS_WITH + ' 1 post', POST_COUNT, len, lambda x: x == 1)
    stats(THREADS_WITH + ' 2 posts', POST_COUNT, len, lambda x: x == 2)
    stats(THREADS_WITH + 'out answers', USERS_COUNT, len, lambda x: x < 2)
    stats(THREADS_WITH + 'out answers contain at most', USERS_COUNT, max, lambda x: x < 2, ' post(s)')
    stats(THREADS_WITH + 'out posts', POST_COUNT, len, lambda x: x == 0)
    stats(THREADS_WITH + ' more than 100 posts', POST_COUNT, len, lambda x: x > 100)
    stats(THREADS_WITH + ' more than 100 posts contain', POST_COUNT, lambda x: x, lambda x: x > 100, ' post(s)')
    
# Bratdateien zum Annotieren erstellen *********************************************************************


def as_brat_indices_with_content(text='', start=0, end=0):

    nl_positions = []
    current_slice = text[start:end].replace('\t', ' ')
    offs = -1

    # handle multiple lines spanning annotations 
    while True:
        offs = current_slice.find('\n', offs + 1)
        
        # no need to fragment if no further line
        if offs == -1:
            break
        
        # empty lines aren't annotated by brat
        if current_slice[offs + 1] == '\n':
            no_newline = re.search(r'[^\n]', current_slice[offs:])
            if no_newline:
                nl_positions.append('%i;%i' % (offs + start, offs + no_newline.start() + start))
                offs += no_newline.start()
        else:
            nl_positions.append('%i;%i' % (offs + start, offs + 1 + start))

    if len(nl_positions) > 0:
        res = '%i %s %i' % (start, ' '.join(nl_positions), end)
    else:
        res = '%i %i' % (start, end)
    current_slice = re.sub(r'\n+', '\n', current_slice)

    # replace the tabs and newlines for the ann file
    return res, current_slice.replace('\n', ' ').strip()


def add_newline(text_merged='', elem_name=None, breduce_space=False):
    if elem_name in BLOCK_TAGS and breduce_space:
        text_merged += '\n'*(2-text_merged[-2:].count('\n'))
    else:
        if elem_name in BLOCK_TAGS[1:]:
            text_merged += '\n\n'
        elif elem_name == BLOCK_TAGS[0]:
            text_merged += '\n'
    return text_merged


def load_block(processed_blocks=None, new_part=None, start_index=0, end_index=0):
    loaded_block = processed_blocks.get(new_part, [start_index, end_index])
    
    # if the block contains more than 1 tag, update the end point
    loaded_block[1] = end_index
    processed_blocks[new_part] = loaded_block


def accumulate_annotations(processed_elements=None, element_type='', text_merged='', brat_annotations=None):
    for start, end in processed_elements:
        brat_annotations.append((element_type,) + as_brat_indices_with_content(text_merged, start, end))


def extract_text_preannotate(soup=None, breduce_space=False):
    
    text_merged = ''
    brat_annotations = []
    processed_imgs = []
    processed_links = []
    processed_blockquotes = dict()
    processed_spoiler_texts = dict()
    spoilers = soup.find_all('div', class_='spoilerBoxContent')
    prev_level = 0
    blocks = 0
    BLOCKQUOTE = 'blockquote'
    CLASS = 'class'
    
    # loop through HTML elements
    for elem in soup.descendants:

        new_text = elem.string

        # ignore empty lines
        if new_text and not new_text.strip():
            continue

        is_image = False
        elem_name = elem.name

        # detect level in the html tree
        # elem.parents is generator -> len() not possible
        # ignore the highest parent ('[document]')
        level = sum(1 for _ in elem.parents) - 1
        
        # if this element is on a deeper level than the previous one
        if prev_level < level:

            # if this element is a new blockelement
            if elem_name in BLOCK_TAGS:
                blocks += 1
                if text_merged and text_merged[-2:] != '\n\n':
                    text_merged = add_newline(text_merged, elem_name, breduce_space)

        # if this element is on the same level as the previous one
        elif prev_level == level:

            # if this element is a new blockelement
            if text_merged and text_merged[-2:] != '\n\n':
                text_merged = add_newline(text_merged, elem_name, breduce_space)

        # if this element is on a higher level than the previous one
        elif prev_level > level:

            # if blockelements are closed
            if level <= blocks:
                if text_merged and text_merged[-2:] != '\n\n':
                    if elem_name in BLOCK_TAGS and breduce_space:
                        text_merged += '\n'*(2-text_merged[-2:].count('\n'))
                    else:
                        if elem_name in BLOCK_TAGS[1:]:
                            text_merged += '\n\n'
                        elif new_text is not None or (new_text is None and elem.contents != []):
                            text_merged += '\n'

            # level of the current highest/last blockelement
            blocks -= blocks - level

        prev_level = level

        # if no line breaks, add space
        if text_merged and text_merged[-1] != '\n':
            text_merged += ' '

        # add the new text
        # if the element is a leaf and a string 
        if elem_name is None:
            new_text = new_text.strip()
            text_merged += new_text
        
        # if the element is a leaf, but not a string 
        else:

            # element is an image
            if elem_name == 'img':
                is_image = True
                if elem.has_attr('alt'):
                    new_text = elem['alt']
                    imglen = len(new_text)
                else:
                    new_text = 'img'
                    imglen = 3
                text_merged += new_text

            # element is another html-element
            else:
                continue

        new_text_len = len(new_text)
        start_index = len(text_merged) - new_text_len
        end_index = start_index + new_text_len
        parents = tuple(elem.parents)[:-1]  # ignore the utmost parent: '[document]'
        parent_names = [p.name for p in parents]

        # preannotation starts here
        # if the HTML element is an image, extract its alternative text and its positions
        if is_image:
            processed_imgs.append([end_index - imglen, end_index])

        # if there is at least one blockquote, extract the positions
        if BLOCKQUOTE in parent_names:
            for p in parents:
                if p.name == BLOCKQUOTE:
                    load_block(processed_blockquotes, p, start_index, end_index)

        # if there is text in a spoiler box, extract the text and its positions
        if elem.string is not None and spoilers:
            for sp in spoilers:
                if sp == elem.parent:
                    load_block(processed_spoiler_texts, sp, start_index, end_index)

        # if there is a link, extract its text and positions
        if 'a' in parent_names:
            a = elem.parent
            a_href = ''

            if a.has_attr('href'):
                a_href = a['href']

            if not a_href:
                if a.has_attr(CLASS):
                    a_class = a[CLASS]
                    if 'button' in a_class:
                        link_type = 'button'
                    else:
                        print('Unknown use of the following link', a)
                else:
                    print('Unknown use of the following link', a)

            # if the link is a userMention
            elif a.has_attr(CLASS) and 'userMention' in a[CLASS]:
                link_type = 'userm'

            # annotate concept depending to link target
            else:
                a_href_rev = a_href[::-1]
                firstslash = a_href_rev.find('/')
                firstdot = a_href_rev.find('.')
                secdot = a_href_rev.find('.', firstdot)
                if firstslash > secdot:
                    end = a_href_rev[:secdot][::-1]
                elif firstslash > firstdot:
                    end = a_href_rev[:firstdot][::-1]
                else:
                    end = ''

                firstquestm = end.find('?')
                if firstquestm > 0:
                    endint = firstquestm
                else:
                    endint = len(end)

                if end[:endint].lower() in ['jpg', 'png', 'jpeg']:
                    link_type = 'pic'
                elif end[:endint].lower() == 'pdf':
                    link_type = 'pdf'
                else:
                    link_type = 'link'

            processed_links.append([start_index, end_index, link_type])

    # convert processed elements to brat annotations; if element spans multiple lines -> brat-fragment
    accumulate_annotations(processed_imgs, 'img', text_merged, brat_annotations)
    accumulate_annotations(processed_blockquotes.values(), BLOCKQUOTE, text_merged, brat_annotations)
    accumulate_annotations(processed_spoiler_texts.values(), 'spoiler', text_merged, brat_annotations)
    for start, end, link_type in processed_links:
        brat_annotations.append((link_type,) + as_brat_indices_with_content(text_merged, start, end))

    return text_merged, brat_annotations


def create_bratfiles(dicthreads=None,
                     brat_folder='',
                     bdelete_old_files=False, bthread_file=False, breduce_space=False,
                     limit_threads=0):

    # if there are old files, delete them
    if bdelete_old_files:
        directory = os.listdir(brat_folder)
        for item in directory:
            if item.endswith('.txt') or item.endswith('.ann'):
                os.remove(os.path.join(brat_folder, item))
        print('old files deleted')

    print('start creating the files')

    # anonymise the user names using numbers
    userids = {}

    thread_digits = len(str(len(dicthreads)))

    def create_txt_ann_files():

        with open(filename + '.ann', 'w', encoding='utf8') as fann:
            if brat_ann_file:
                for line in brat_ann_file:
                    fann.write(line + '\n')
            else:
                fann.write('')
        with open(filename + '.txt', 'w', encoding='utf8') as ftxt:
            ftxt.write(text_merged)

    # if all posts of one thread shall be in one file
    if bthread_file:

        for threadnr, (threadid, dicthread) in enumerate(dicthreads.items(), start=1):
            posts = ''
            processed_users = []
            userids[threadid] = {}
            userid = -1

            # file creation may be limited here
            if limit_threads and threadnr > limit_threads:
                break

            for dicpost in dicthread:
                username = dicpost['username']
                if username not in processed_users:
                    userid += 1
                    userids[threadid][username] = userid
                    processed_users.append(username)
                posts += '<div><p>__________user%i__________</p>' % userids[threadid][username] + dicpost['post-html']\
                         + '</div>'

            # parse HTML, extract and preannotate the text
            soup = BeautifulSoup(posts, 'html.parser')
            text_merged, brat_annotations = extract_text_preannotate(soup, breduce_space)

            filename = brat_folder + 'Thread_' + str(threadnr).zfill(thread_digits)
            brat_ann_file = ['T%i\t%s %s\t%s' % (nr, anno_type, positions, text)
                             for nr, (anno_type, positions, text)
                             in enumerate(brat_annotations, start=1)]
            create_txt_ann_files()

    # if every post shall be in a seperate file
    else:

        postnr = 0
        post_digits = len(str(sum(len(posts) for posts in dicthreads.values())))

        for threadnr, (threadid, dicthread) in enumerate(dicthreads.items(), start=1):
            processed_users = []
            userids[threadid] = {}
            userid = -1

            # file creation may be limited here
            if limit_threads and threadnr > limit_threads:
                break

            for dicpost in dicthread:

                # parse HTML, extract and preannotate the text
                soup = BeautifulSoup(dicpost['post-html'], 'html.parser')
                text_merged, brat_annotations = extract_text_preannotate(soup, breduce_space)

                # prepare file name
                postnr += 1
                username = dicpost['username']
                if username not in processed_users:
                    userid += 1
                    userids[threadid][username] = userid
                    processed_users.append(username)

                filename = '%sPost%s_Thread%s_User%i' % (
                    brat_folder, str(postnr).zfill(post_digits),
                    str(threadnr).zfill(thread_digits), userids[threadid][username]
                    )
                brat_ann_file = ['T%i\t%s %s\t%s' % (nr, anno_type, positions, text)
                                 for nr, (anno_type, positions, text)
                                 in enumerate(brat_annotations, start=1)]
                create_txt_ann_files()

    print('files created')


def main(input_file: ('input file name', 'option', 'i')='/home/olli/Dokumente/Portfolio/dfki_webscraping-master/med1/med1.1.jl',
         brat_folder: ('brat folder', 'option', 'b')='/mnt/e/brat-v1.3_Crunchy_Frog/data/medscrape/',
         limit_threads: ('limit', 'option', 'l')=200,
         bnew_files: ('', 'flag', 'n')=False,
         bshow_statistics: ('', 'flag', 's')=False,
         bthread_file: ('', 'flag', 't')=False,
         bdelete_old_files: ('','flag', 'd')=False,
         breduce_space: ('','flag', 'r')=False):
    """
    when indicated, extracts forum posts from jl file, preannotates them (citations, smileys, pictures, links)
    when indicated, show statistics
    when indicated, delete the old txt and ann files before creating the new files
    requires jl file with scraped posts and additional information concerning the posts from med1.de

    :param input_file: jl file with posts and further informations, created by med1.py (scrapy script)
    :param brat_folder: data directory in the brat folder for the txt and ann files 
    :param bnew_files: True if you want to create new files
    :param bshow_statistics: True if you want to show the statistics
    :param bthread_file: True if one txt and ann file don't contain one individual post but all posts from one thread
    :param bdelete_old_files: True if you want to delete the old files and if bnew_files == True
    :param breduce_space: True if you want to avoid consecutive blank lines
    """

    # Load data *******************************************************************************************
    with open(input_file, encoding='utf8') as data_file:
        adata_lines = data_file.readlines()
    adata = [json.loads(dicline) for dicline in adata_lines]

    # Group data into threads 
    dicthreads = defaultdict(list)
    for dicpost in adata:
        dicthreads[dicpost['thread-id']].append(dicpost)

    if bshow_statistics:
        show_statistics(dicthreads)

    if bnew_files:
        create_bratfiles(dicthreads, brat_folder, bdelete_old_files, bthread_file, breduce_space, limit_threads)


if __name__ == '__main__':
    plac.call(main)
