from string_gen import StringGen
from uuid import uuid4

if __name__ == '__main__':
    generator = StringGen(r'\d')
    print(generator.render_set(10))
