import sys

if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        c = 0
        contents = []
        in_contents = False
        lines = f.readlines()
        qa_flag = "Question"
        for line in lines:
            sent = line.strip()
            if sent.endswith('</contents>'):
                in_contents = False
            if sent == '<contents>' or in_contents:
                in_contents = True
                c += 1
                if c > 3:
                    if sent:
                        contents.append(line.strip())
                    if not sent and qa_flag == "Question":
                        contents.append(line.strip())
                        qa_flag = "Answer"

        for sent in contents:
            print sent
