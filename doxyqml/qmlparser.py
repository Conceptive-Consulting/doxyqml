import lexer

from qmlclass import QmlArgument, QmlProperty, QmlFunction, QmlSignal


class QmlParserError(Exception):
    def __init__(self, msg, token):
        Exception.__init__(self, msg)
        self.token = token


class QmlParserUnexpectedTokenError(QmlParserError):
    def __init__(self, token):
        QmlParserError.__init__(self, "Unexpected token: %s" % str(token), token)


class ClassParser(object):
    def parse(self, main):
        token = main.consume_wo_comments()
        if token.type != lexer.BLOCK_START:
            raise QmlParserError("Expected '{' after base class name", token)
        comments = []
        while not main.at_end():
            token = main.consume()
            if token.type == lexer.COMMENT:
                comments.append(token.value)
            else:
                done = self.parse_token(main, token, comments)
                if done:
                    return
                comments = []

    def parse_token(self, main, token, comments):
        # Should we just use the last comment?
        doc = "\n".join(comments)
        if token.type == lexer.KEYWORD:
            if token.value == "property":
                obj = parse_property(main)
                obj.doc = doc
                main.dst.properties.append(obj)
            elif token.value == "function":
                obj = parse_function(main)
                obj.doc = doc
                main.dst.functions.append(obj)
            elif token.value == "signal":
                obj = parse_signal(main)
                obj.doc = doc
                main.dst.signals.append(obj)
            else:
                raise QmlParserError("Unknown keyword '%s'" % token.value, token)

        elif token.type == lexer.BLOCK_START:
            skip_block(main)

        elif token.type == lexer.BLOCK_END:
            return True

        return False


def parse_property(reader):
    prop = QmlProperty()
    token = reader.consume_expecting(lexer.ELEMENT)
    if token.value == "default":
        prop.default = True
        token = reader.consume_expecting(lexer.ELEMENT)

    prop.type = token.value

    token = reader.consume_expecting(lexer.ELEMENT)
    prop.name = token.value
    return prop


def parse_function(reader):
    obj = QmlFunction()
    token = reader.consume_expecting(lexer.ELEMENT)
    obj.name = token.value

    reader.consume_expecting(lexer.CHAR, "(")
    obj.args = parse_arguments(reader)
    return obj


def parse_signal(reader):
    obj = QmlSignal()
    token = reader.consume_expecting(lexer.ELEMENT)
    obj.name = token.value

    idx = reader.idx
    token = reader.consume_wo_comments()
    if token.type == lexer.CHAR and token.value == "(":
        obj.args = parse_arguments(reader, typed=True)
    else:
        reader.idx = idx
    return obj


def parse_arguments(reader, typed=False):
    token = reader.consume_wo_comments()
    if token.type == lexer.CHAR and token.value == ")":
        return []
    elif token.type != lexer.ELEMENT:
        raise QmlParserUnexpectedTokenError(token)

    args = []
    while True:
        if typed:
            arg_type = token.value
            token = reader.consume_expecting(lexer.ELEMENT)
            arg = QmlArgument(token.value)
            arg.type = arg_type
        else:
            arg = QmlArgument(token.value)
        args.append(arg)

        token = reader.consume_expecting(lexer.CHAR)
        if token.value == ")":
            return args
        elif token.value != ",":
            raise QmlParserUnexpectedTokenError(token)

        token = reader.consume_expecting(lexer.ELEMENT)


def skip_block(reader):
    count = 1
    while True:
        token = reader.consume_wo_comments()
        if token.type == lexer.BLOCK_START:
            count += 1
        elif token.type == lexer.BLOCK_END:
            count -= 1
            if count == 0:
                return


def parse_header(reader, cls):
    while not reader.at_end():
        token = reader.consume()
        if token.type == lexer.COMMENT:
            cls.comments.append(token.value)
        elif token.type == lexer.IMPORT:
            pass
        elif token.type == lexer.ELEMENT:
            cls.base_name = token.value
            return
        else:
            raise QmlParserUnexpectedTokenError(token)


class TokenReader(object):
    def __init__(self, dst, tokens):
        self.dst = dst
        self.tokens = tokens
        self.idx = 0

    def consume(self):
        token = self.tokens[self.idx]
        self.idx += 1
        return token

    def consume_wo_comments(self):
        while True:
            token = self.consume()
            if token.type != lexer.COMMENT:
                return token

    def consume_expecting(self, type, value=None):
        token = self.consume_wo_comments()
        if token.type != type:
            raise QmlParserError("Expected token of type '%s', got '%s' instead" % (type, token.type), token)
        if value is not None and token.value != value:
            raise QmlParserError("Expected token with value '%s', got '%s' instead" % (value, token.value), token)
        return token

    def at_end(self):
        return self.idx == len(self.tokens)


def parse(cls, tokens):
    reader = TokenReader(cls, tokens)
    parse_header(reader, cls)
    ClassParser().parse(reader)
