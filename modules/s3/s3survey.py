# -*- coding: utf-8 -*-

"""
    Custom UI Widgets used by the survey application

    @copyright: 2009-2011 (c) Sahana Software Foundation
    @license: MIT

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use,
    copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following
    conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.
"""

import sys

from xml.sax.saxutils import unescape

try:
    from cStringIO import StringIO    # Faster, where available
except:
    from StringIO import StringIO

from gluon.sqlhtml import *
import gluon.contrib.simplejson as json
from gluon import *

DEBUG = False
if DEBUG:
    print >> sys.stderr, "S3Survey: DEBUG MODE"
    def _debug(m):
        print >> sys.stderr, m
else:
    _debug = lambda m: None

# -----------------------------------------------------------------------------
class DataMatrix():
    """
        Class that sets the data up ready for export to a specific format,
        such as a spreadsheet or a PDF document.
        
        It holds the data in a matrix with each element holding details on:
         * A unique position
         * The actual text to be displayed
         * Any style to be applied to the data
    """
    def __init__(self):
        self.matrix = {}
        self.lastRow = 0

    def addElement(self, element):
        """
            Add an element to the matrix, checking that the position is unique.
        """
        posn = element.posn()
        if posn in self.matrix:
            msg = "Attempting to add data %s at posn %s. This is already taken with data %s" % \
                        (element, posn, self.matrix[posn])
            raise Exception(msg)
        self.matrix[posn] = element
        element.parents.append(self)
        if element.merged():
            self.joinElements(element)
        if element.row > self.lastRow:
            self.lastRow = element.row 

    def joinedElementStyles(self, rootElement):
        """
            return a list of all the styles used by all the elements joined
            to the root element
        """
        styleList = []
        row = rootElement.row
        col = rootElement.col
        for v in range(rootElement.mergeV + 1):
            for h in range(rootElement.mergeH + 1):
                newPosn = "%s,%s" % (row + v, col + h)
                styleList += self.matrix[newPosn].styleList
        return styleList

    def joinElements(self, rootElement):
        """
            This will set the joinedWith property to the posn of rootElement
            for all the elements that rootElement joins with to make a single
            large merged element.
        """
        row = rootElement.row
        col = rootElement.col
        posn = rootElement.posn()
        for v in range(rootElement.mergeV + 1):
            for h in range(rootElement.mergeH + 1):
                newPosn = "%s,%s" % (row + v, col + h)
                if newPosn == posn:
                    continue
                if newPosn in self.matrix:
                    if self.matrix[newPosn].joinedWith == posn:
                        continue
                    msg = "Attempting to merge element at posn %s. The following data will be lost %s" % \
                                (newPosn, self.matrix[newPosn])
                    self.matrix[newPosn].joinedWith = posn
                else:
                    childElement = MatrixElement(row, col, "", [])
                    childElement.joinedWith = posn
                    self.matrix[newPosn] = childElement

    def boxRange(self, startrow, startcol, endrow, endcol):
        """
            Function to add a bounding box around the elements contained by
            the elements (startrow, startcol) and (endrow, endcol)

            This uses standard style names:
            boxL, boxB, boxR, boxT
            for Left, Bottom, Right and Top borders respectively
        """
        for r in range(startrow, endrow):
            posn = "%s,%s" % (r, startcol)
            if posn in self.matrix:
                self.matrix[posn].styleList.append("boxL")
            else:
                self.addElement(MatrixElement(r, startcol, "", "boxL"))
            posn = "%s,%s" % (r, endcol)
            if posn in self.matrix:
                self.matrix[posn].styleList.append("boxR")
            else:
                self.addElement(MatrixElement(r, endcol, "", "boxR"))
        for c in range(startcol, endcol + 1):
            posn = "%s,%s" % (startrow, c)
            if posn in self.matrix:
                self.matrix[posn].styleList.append("boxT")
            else:
                self.addElement(MatrixElement(startrow, c, "", "boxT"))
            posn = "%s,%s" % (endrow - 1, c)
            if posn in self.matrix:
                self.matrix[posn].styleList.append("boxB")
            else:
                self.addElement(MatrixElement(endrow - 1, c, "", "boxB"))


# -----------------------------------------------------------------------------
class MatrixElement():
    """
        Class that holds the details of a single element in the matrix
        
        * posn - row & col
        * text - the actual data that will be displayed at the given position
        * style - a list of styles that will be applied to this location
    """
    def __init__(self, row, col, data, style):
        self.row = row
        self.col = col
        self.text = data
        self.mergeH = 0
        self.mergeV = 0
        self.joinedWith = None
        self.parents = []
        if isinstance(style, list):
            self.styleList = style
        else:
            self.styleList = [style]

    def __repr__(self):
        return self.text

    def merge(self, horizontal=0, vertical=0):
        self.mergeH = horizontal
        self.mergeV = vertical
        for parent in self.parents:
            parent.joinElements(self)

    def posn(self):
        """ Standard representation of the position """
        return "%s,%s" % (self.row, self.col)

    def nextX(self):
        return self.row + self.mergeH + 1

    def nextY(self):
        return self.col + self.mergeV + 1

    def merged(self):
        if self.mergeH > 0 or self.mergeV > 0:
            return True
        return False

    def joined(self):
        if self.joinedWith == None:
            return False
        else:
            return True

# -----------------------------------------------------------------------------
# Question Types
def survey_stringType(question_id = None):
    return S3QuestionTypeStringWidget(question_id)
def survey_textType(question_id = None):
    return S3QuestionTypeTextWidget(question_id)
def survey_numericType(question_id = None):
    return S3QuestionTypeNumericWidget(question_id)
def survey_dateType(question_id = None):
    return S3QuestionTypeDateWidget(question_id)
def survey_optionType(question_id = None):
    return S3QuestionTypeOptionWidget(question_id)
def survey_ynType(question_id = None):
    return S3QuestionTypeOptionYNWidget(question_id)
def survey_yndType(question_id = None):
    return S3QuestionTypeOptionYNDWidget(question_id)
def survey_optionOtherType(question_id = None):
    return S3QuestionTypeOptionOtherWidget(question_id)
def survey_multiOptionType(question_id = None):
    return S3QuestionTypeMultiOptionWidget(question_id)
def survey_locationType(question_id = None):
    return S3QuestionTypeLocationWidget(question_id)
def survey_linkType(question_id = None):
    return S3QuestionTypeLinkWidget(question_id)
def survey_ratingType(question_id = None):
    pass
def survey_gridType(question_id = None):
    return S3QuestionTypeGridWidget(question_id)
def survey_gridChildType(question_id = None):
    return S3QuestionTypeGridChildWidget(question_id)
def survey_T(phrase, langDict):
    """
        Function to translate a phrase using the dictionary passed in
    """
    if phrase in langDict and langDict[phrase] != "":
        return langDict[phrase]
    else:
        return phrase


survey_question_type = {
    "String": survey_stringType,
    "Text": survey_textType,
    "Numeric": survey_numericType,
    "Date": survey_dateType,
    "Option": survey_optionType,
    "YesNo": survey_ynType,
    "YesNoDontKnow": survey_yndType,
    "OptionOther": survey_optionOtherType,
    "MultiOption" : survey_multiOptionType,
    "Location": survey_locationType,
    "Link" : survey_linkType,
#    "Rating": survey_ratingType,
    "Grid" : survey_gridType,
    "GridChild" : survey_gridChildType,
}

##########################################################################
# Class S3QuestionTypeAbstractWidget
##########################################################################
class S3QuestionTypeAbstractWidget(FormWidget):
    """
        Abstract Question Type widget

        A QuestionTypeWidget can have three basic states:

        The first is as a descriptor for the type of question.
        In this state it will hold the information about what this type of
        question may look like.

        The second state is when it is associated with an actual question
        on the database. Then it will additionally hold information about what
        this actual question looks like.

        The third state is when the widget of an actual question is
        associated with a single answer to that question. If that happens then
        the self.question record from the database is extended to hold
        the actual answer and the complete_id of that answer.

        For example: A numeric question type has a metadata value of "Format"
        this can be used to describe how the data could be formatted to
        represent a number. When this question type is associated with an
        actual numeric question then the metadata might be "Format" : n, which
        would mean that it is an integer value.

        The general instance variables:

        @ivar metalist: A list of all the valid metadata descriptors. This would
                        be used by a UI when designing a question
        @ivar attr: Any HTML/CSS attributes passed in by the call to display
        @ivar webwidget: The web2py widget that should be used to display the
                         question type
        @ivar typeDescription: The description of the type when it is displayed
                               on the screen such as in reports 

        The instance variables when the widget is associated with a question:

        @ivar id: The id of the question from the survey_question table
        @ivar question: The question record from the database.
                        Note this variable can be extended to include the
                        answer taken from the complete_id, allowing the
                        question to hold a single answer. This is needed when
                        updating responses.
        @ivar qstn_metadata: The actual metadata for this question taken from
                             the survey_question_metadata table and then
                             stored as a descriptor value pair
        @ivar field: The field object from metadata table, which can be used
                     by the widget to add additional rules (such as a requires)
                     before setting up the UI when inputing data

        @author: Graeme Foster (graeme at acm dot org)

    """

    def __init__(self,
                 question_id
                ):
        self.ANSWER_VALID = 0
        self.ANSWER_MISSING = 1
        self.ANSWER_PARTLY_VALID = 2
        self.ANSWER_INVALID = 3

        T = current.T
        db = current.db
        # The various database tables that the widget may want access to
        self.qtable = db.survey_question
        self.mtable = db.survey_question_metadata
        self.qltable = db.survey_question_list
        self.ctable = db.survey_complete
        self.atable = db.survey_answer
        # the general instance variables
        self.metalist = ["Help message"]
        self.attr = {}
        self.webwidget = StringWidget
        self.typeDescription = None
        # The instance variables when the widget is associated with a question
        self.id = question_id
        self.question = None
        self.qstn_metadata = {}
        # Initialise the metadata from the question_id
        self._store_metadata()
        self.field = self.mtable.value

        try:
            from xlwt.Utils import rowcol_to_cell
            self.rowcol_to_cell = rowcol_to_cell
        except:
            import sys
            print >> sys.stderr, "WARNING: S3Survey: xlwt module needed for XLS export"

    def _store_metadata(self, qstn_id=None, update=False):
        """
            This will store the question id in self.id,
            the question data in self.question, and
            the metadata for this specific question in self.qstn_metadata

            It will only get the data from the db if it hasn't already been
            retrieved, or if the update flag is True
        """
        if qstn_id != None:
            if self.id != qstn_id:
                self.id = qstn_id
                # The id has changed so force an update
                update = True
        if self.id == None:
            self.question = None
            self.qstn_metadata = {}
            return
        if self.question == None or update:
            db = current.db
            # Get the question from the database
            query = (self.qtable.id == self.id)
            self.question = db(query).select(limitby=(0, 1)).first()
            if self.question == None:
                raise Exception("no question with id %s in database" % self.id)
            # Get the metadata from the database and store in qstn_metadata
            query = (self.mtable.question_id == self.id)
            self.rows = db(query).select()
            for row in self.rows:
                # Remove any double quotes from around the data before storing 
                self.qstn_metadata[row.descriptor] = row.value.strip('"')

    def get(self, value, default=None):
        """
            This will return a single metadata value held by the widget
        """
        if value in self.qstn_metadata:
            return self.qstn_metadata[value]
        else:
            return default

    def set(self, value, data):
        """
            This will store a single metadata value
        """
        self.qstn_metadata[value] = data


    def getAnswer(self):
        """
            Return the value of the answer for this question
        """
        if "answer" in self.question:
            answer = self.question.answer
        else:
            answer = ""
        return answer

    def repr(self, value=None):
        """
            function to format the answer, which can be passed in
        """
        if value == None:
            value = getAnswer()
        return value

    def loadAnswer(self, complete_id, question_id, forceDB=False):
        """
            This will return a value held by the widget
            The value can be held in different locations
            1) In the widget itself:
            2) On the database: table.survey_complete
        """
        value = None
        self._store_metadata(question_id)
        if "answer" in self.question and \
           self.question.complete_id == complete_id and \
           forceDB == False:
            answer = self.question.answer
        else:
            query = (self.atable.complete_id == complete_id) & \
                    (self.atable.question_id == question_id)
            row = current.db(query).select(limitby=(0, 1)).first()
            if row != None:
                value = row.value
                self.question["answer"] = value
            self.question["complete_id"] = complete_id
        return value

    def initDisplay(self, **attr):
        """
            This method set's up the variables that will be used by all
            display methods of fields for the question type.
            It uses the metadata to define the look of the field
        """
        if "question_id" in attr:
            self.id = attr["question_id"]
        if self.id == None:
            raise Exception("Need to specify the question_id for this QuestionType")
        qstn_id = self.id
        self._store_metadata(qstn_id)
        attr["_name"] = self.question.code
        self.attr = attr

    def display(self, **attr):
        """
            This displays the widget on a web form. It uses the layout
            function to control how the widget is displayed
        """
        self.initDisplay(**attr)
        value = self.getAnswer()
        input = self.webwidget.widget(self.field, value, **self.attr)
        return self.layout(self.question.name, input, **attr)

    def layout(self, label, widget, **attr):
        """
            This lays the label widget that is passed in on the screen.

            Currently it has a single default layout mechanism but in the
            future it will be possible to add more which will be controlled
            vis the attr passed into display and stored in self.attr
        """
        if "display" in attr:
            display = attr["display"]
        else:
            display = "Default"
        if display == "Default":
            elements = []
            elements.append(TR(TH(label), TD(widget),
                               _class="survey_question"))
            return TAG[""](elements)
        elif display == "Control Only":
            return TD(widget)

    def onaccept(self, value):
        """
            Method to format the value that has just been put on the database
        """
        return value

    def type_represent(self):
        """
            Display the type in a DIV for displaying on the screen
        """
        return DIV(self.typeDescription, _class="surveyWidgetType")

    def _Tquestion(self, langDict):
        """
            Function to translate the question using the dictionary passed in
        """
        return survey_T(self.question["name"], langDict)

    def writeToMatrix(self,
                      matrix, 
                      row,
                      col,
                      langDict=dict(),
                      answerMatrix=None,
                      style={"Label": True
                            ,"LabelLeft" : True
                            },
                      ):
        """
            Function to write out basic details to the matrix object
        """
        self._store_metadata()
        if "Label" in style and style["Label"]:
            cell = MatrixElement(row, col, self._Tquestion(langDict),
                                 style="styleSubHeader")
            matrix.addElement(cell)
            if "LabelLeft" in style and style["LabelLeft"]:
                col += 1
            else:
                row += 1
        cell = MatrixElement(row,col,"", style="styleInput")
        matrix.addElement(cell)
        if answerMatrix != None:
            answerRow = answerMatrix.lastRow+1
            cell = MatrixElement(answerRow, 0, self.question["code"],
                                 style="styleSubHeader")
            answerMatrix.addElement(cell)
            cell = MatrixElement(answerRow, 3,
                                 self.rowcol_to_cell(row, col),
                                 style="styleText")
            answerMatrix.addElement(cell)
        return (row+1, col+1)


    ######################################################################
    # Functions not fully implemented or used
    ######################################################################
    def validate(self, valueList, qstn_id):
        """
            This will validate the data passed in to the widget

            NOTE: Not currently used but will be used when the UI supports the
                  validation of data entered in to the web form
        """
        if len(valueList) == 0:
            return self.ANSWER_MISSING
        data = value(valueList, 0)
        if data == None:
            return self.ANSWER_MISSING
        length = self.get("Length")
        if length != None and length(data) > length:
            return ANSWER_PARTLY_VALID
        return self.ANSWER_VALID

    def metadata(self, **attr):
        """
            Create the input fields for the metadata for the QuestionType

            NOTE: Not currently used but will be used when the UI supports the
                  creation of the template and specifically the questions in
                  the template 
        """
        if "question_id" in attr:
            self._store_metadata(attr["question_id"])
        elements = []
        for fieldname in self.metalist:
            value = self.get(fieldname, "")
            input = StringWidget.widget(self.field, value, **attr)
            elements.append(TR(TD(fieldname), TD(input)))
        return TAG[""](elements)


##########################################################################
# Class S3QuestionTypeTextWidget
##########################################################################
class S3QuestionTypeTextWidget(S3QuestionTypeAbstractWidget):
    """
        Text Question Type widget

        provides a widget for the survey module that will manage plain
        text questions.

        Available metadata for this class:
        Help message: A message to help with completing the question

        @author: Graeme Foster (graeme at acm dot org)
    """

    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        self.webwidget = TextWidget
        self.typeDescription = T("Long Text")

##########################################################################
# Class S3QuestionTypeStringWidget
##########################################################################
class S3QuestionTypeStringWidget(S3QuestionTypeAbstractWidget):
    """
        String Question Type widget

        provides a widget for the survey module that will manage plain
        string questions (text with a limited length).

        Available metadata for this class:
        Help message: A message to help with completing the question
        Length:       The number of characters

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        T = current.T
        self.metalist.append("Length")
        self.typeDescription = T("Short Text")

    def display(self, **attr):
        if "length" in self.qstn_metadata:
            length = self.qstn_metadata["length"]
            attr["_size"] = length
            attr["_maxlength"] = length
        return S3QuestionTypeAbstractWidget.display(self, **attr)

##########################################################################
# Class S3QuestionTypeNumericWidget
##########################################################################
class S3QuestionTypeNumericWidget(S3QuestionTypeAbstractWidget):
    """
        Numeric Question Type widget

        provides a widget for the survey module that will manage simple
        numerical questions.

        Available metadata for this class:
        Help message: A message to help with completing the question
        Length:       The length if the number, default length of 10 characters
        Format:       Describes the makeup of the number, as follows:
                      n    integer
                      n.   floating point
                      n.n  floating point, the number of decimal places defined
                           by the number of n's that follow the decimal point

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        T = current.T
        self.metalist.append("Length")
        self.metalist.append("Format")
        self.typeDescription = T("Numeric") 

    def display(self, **attr):
        length = self.get("length", 10)
        attr["_size"] = length
        attr["_maxlength"] = length
        return S3QuestionTypeAbstractWidget.display(self, **attr)

    def onaccept(self, value):
        """
            Method to format the value that has just been put on the database
        """
        return str(self.formattedAnswer(value))

    def formattedAnswer(self, data, format=None):
        if format == None:
            format = self.get("Format", "n")
        parts = format.partition(".")
        try:
            result = float(data)
        except:
            result = 0
        if parts[1] == "": # No decimal point so must be a whole number
            return int(result)
        else:
            if parts[2] == "": # No decimal places specified
                return result
            else:
                return round(result, len(parts[2]))


    ######################################################################
    # Functions not fully implemented or used
    ######################################################################
    def validate(self, valueList, qstn_id):
        """
            This will validate the data passed in to the widget
        """
        result = S3QuestionTypeAbstractWidget.validate(self, valueList)
        if result != ANSWER_VALID:
            return result
        length = self.get("length", 10)
        format = self.get("format")
        data = value(valueList, 0)
        if format != None:
            try:
                self.formattedValue(data, format)
                return self.ANSWER_VALID
            except exceptions.ValueError:
                return self.ANSWER_INVALID

        return self.ANSWER_VALID

##########################################################################
# Class S3QuestionTypeDateWidget
##########################################################################
class S3QuestionTypeDateWidget(S3QuestionTypeAbstractWidget):
    """
        Date Question Type widget

        provides a widget for the survey module that will manage simple
        date questions.

        Available metadata for this class:
        Help message: A message to help with completing the question

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        self.typeDescription = T("Date")

    def display(self, **attr):
        from s3widgets import S3DateWidget
        value = self.getAnswer()
        widget = S3DateWidget()
#        self.field.name = self.question.code
        input = widget(self.field, value, **self.attr)
        return self.layout(self.question.name, input, **attr)
#        length = 30
#        attr["_size"] = length
#        attr["_maxlength"] = length
#        return S3QuestionTypeAbstractWidget.display(self, **attr)

    def formattedAnswer(self, data):
        """
            This will take a string and do it's best to return a Date object
            It will try the following in order
            * Convert using the ISO format:
            * look for a month in words a 4 digit year and a day (1 or 2 digits)
            * a year and month that matches the date now and NOT a future date
            * a year that matches the current date and the previous month
        """
        rawDate = data
        date = None
        try:
            # First convert any non-numeric to a hyphen
            isoDate = ""
            addHyphen = False
            for char in rawDate:
                if char.isdigit:
                    if addHyphen == True and isoDate != "":
                        iscDate += "-"
                    isoDate += char
                    addHyphen = False
                else:
                    addHyphen = True
            # @ToDo: Use deployment_settings.get_L10n_date_format()
            date = datetime.strptime(rawDate, "%Y-%m-%d")
            return date
        except ValueError:
            try:
                for month in monthList:
                    if month in rawDate:
                        search = re,search("\D\d\d\D", rawDate)
                        if search:
                            day = search.group()
                        else:
                            search = re,search("^\d\d\D", rawDate)
                            if search:
                                day = search.group()
                            else:
                                search = re,search("\D\d\d$", rawDate)
                                if search:
                                    day = search.group()
                                else:
                                    search = re,search("\D\d\D", rawDate)
                                    if search:
                                        day = "0" + search.group()
                                    else:
                                        search = re,search("^\d\D", rawDate)
                                        if search:
                                            day = "0" + search.group()
                                        else:
                                            search = re,search("\D\d$", rawDate)
                                            if search:
                                                day = "0" + search.group()
                                            else:
                                                raise ValueError
                        search = re,search("\D\d\d\d\d\D", rawDate)
                        if search:
                            year = search.group()
                        else:
                            search = re,search("^\d\d\d\d\D", rawDate)
                            if search:
                                year = search.group()
                            else:
                                search = re,search("\D\d\d\d\d$", rawDate)
                                if search:
                                    year = search.group()
                                else:
                                    raise ValueError
                    # @ToDo: Use deployment_settings.get_L10n_date_format()
                    testDate = "%s-%s-%s" % (day, month, year)
                    if len(month) == 3:
                        format == "%d-%b-%Y"
                    else:
                        format == "%d-%B-%Y"
                    date = datetime.strptime(format, testDate)
                    return date
            except ValueError:
                return date


    ######################################################################
    # Functions not fully implemented or used
    ######################################################################
    def validate(self, valueList, qstn_id):
        """
            This will validate the data passed in to the widget
        """
        result = S3QuestionTypeAbstractWidget.validate(self, valueList)
        if result != ANSWER_VALID:
            return result
        length = self.get("length", 10)
        format = self.get("format")
        data = value(valueList, 0)
        if format != None:
            try:
                self.formattedValue(data, format)
                return self.ANSWER_VALID
            except exceptions.ValueError:
                return self.ANSWER_INVALID

        return self.ANSWER_VALID

##########################################################################
# Class S3QuestionTypeOptionWidget
##########################################################################
class S3QuestionTypeOptionWidget(S3QuestionTypeAbstractWidget):
    """
        Option Question Type widget

        provides a widget for the survey module that will manage simple
        option questions.

        Available metadata for this class:
        Help message: A message to help with completing the question
        Length:       The number of options
        #:            A number one for each option

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        T = current.T
        self.selectionInstructions = "Type x to mark box. Select just one option"
        self.metalist.append("Length")
        self.webwidget = RadioWidget
        self.typeDescription = T("Option") 

    def display(self, **attr):
        S3QuestionTypeAbstractWidget.initDisplay(self, **attr)
        self.field.requires = IS_IN_SET(self.getList())
        value = self.getAnswer()
        self.field.name = self.question.code
        input = RadioWidget.widget(self.field, value, **self.attr)
        self.field.name = "value"
        return self.layout(self.question.name, input, **attr)

    def getList(self):
        list = []
        length = self.get("Length")
        if length == None:
            raise Exception("Need to have the options specified")
        for i in range(int(length)):
            list.append(self.get(str(i + 1)))
        return list

    def writeToMatrix(self,
                      matrix,
                      row,
                      col,
                      langDict=dict(),
                      answerMatrix=None,
                      style={"Label" : True,
                             "LabelLeft" : False
                            }
                     ):
        """
            Function to write out basic details to the matrix object
        """
        self._store_metadata()
        if "Label" in style and style["Label"]:
            cell = MatrixElement(row, col, self._Tquestion(langDict),
                                 style="styleSubHeader")
            matrix.addElement(cell)
            if "LabelLeft" in style and style["LabelLeft"]:
                col += 1
                if self.selectionInstructions != None:
                    cell = MatrixElement(row,
                                         col,
                                         survey_T(self.selectionInstructions,
                                                  langDict),
                                         style="styleInstructions",
                                         )
                    matrix.addElement(cell)
                    col += 1
            else:
                cell.merge(horizontal=1)
                row += 1
                if self.selectionInstructions != None:
                    cell = MatrixElement(row, col, 
                                         survey_T(self.selectionInstructions,
                                                  langDict),
                                         style="styleInstructions")
                    matrix.addElement(cell)
                    cell.merge(horizontal=1)
                    row += 1
        list = self.getList()
        if answerMatrix != None:
            answerRow = answerMatrix.lastRow+1
            cell = MatrixElement(answerRow, 0, self.question["code"],
                                 style="styleSubHeader")
            answerMatrix.addElement(cell)
            cell = MatrixElement(answerRow, 1, len(list),
                                 style="styleSubHeader")
            answerMatrix.addElement(cell)
            cell = MatrixElement(answerRow, 2, "|#|".join(list),
                                 style="styleSubHeader")
            answerMatrix.addElement(cell)
            answerCol = 3
        for option in list:
            cell = MatrixElement(row, col, survey_T(option, langDict),
                                 style="styleText")
            matrix.addElement(cell)
            cell = MatrixElement(row, col+1,"", style="styleInput")
            matrix.addElement(cell)
            if answerMatrix != None:
                cell = MatrixElement(answerRow, answerCol,
                                     self.rowcol_to_cell(row, col + 1),
                                     style="styleText")
                answerMatrix.addElement(cell)
                answerCol += 1
            row += 1
        return (row, col+2)


    ######################################################################
    # Functions not fully implemented or used
    ######################################################################
    def validate(self, valueList, qstn_id):
        """
            This will validate the data passed in to the widget
        """
        if len(valueList) == 0:
            return self.ANSWER_MISSING
        data = valueList[0]
        if data == None:
            return self.ANSWER_MISSING
        self._store_metadata(qstn_id)
        if data in self.getList():
            return self.ANSWER_VALID
        else:
            return self.ANSWER_VALID
        return self.ANSWER_INVALID

##########################################################################
# Class S3QuestionTypeOptionYNWidget
##########################################################################
class S3QuestionTypeOptionYNWidget(S3QuestionTypeOptionWidget):
    """
        YN Question Type widget

        provides a widget for the survey module that will manage simple
        yes no questions.

        Available metadata for this class:
        Help message: A message to help with completing the question

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeOptionWidget.__init__(self, question_id)
        self.selectionInstructions = "Type x to mark box."
        self.typeDescription = T("Yes, No")
        self.qstn_metadata["Length"] = 2

    def getList(self):
        return ["Yes", "No"]
#        T = current.T
#        return [T("Yes"), T("No")]


##########################################################################
# Class S3QuestionTypeOptionYNDWidget
##########################################################################
class S3QuestionTypeOptionYNDWidget(S3QuestionTypeOptionWidget):
    """
        Yes, No, Don't Know: Question Type widget

        provides a widget for the survey module that will manage simple
        yes no questions.

        Available metadata for this class:
        Help message: A message to help with completing the question

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeOptionWidget.__init__(self, question_id)
        self.selectionInstructions = "Type x to mark box."
        self.typeDescription = T("Yes, No, Don't Know")
        self.qstn_metadata["Length"] = 3

    def getList(self):
        return ["Yes", "No", "Don't Know"]
#        T = current.T
#        return [T("Yes"), T("No"), T("Don't Know")]


##########################################################################
# Class S3QuestionTypeOptionOtherWidget
##########################################################################
class S3QuestionTypeOptionOtherWidget(S3QuestionTypeOptionWidget):
    """
        Option Question Type widget with a final other option attached 

        provides a widget for the survey module that will manage simple
        yes no questions.

        Available metadata for this class:
        Help message: A message to help with completing the question
        Length:       The number of options
        #:            A number one for each option
        Other:        The question type the other option should be

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeOptionWidget.__init__(self, question_id)
        self.typeDescription = T("Option Other")

    def getList(self):
        list = S3QuestionTypeOptionWidget.getList(self)
        list.append("Other")
        return list


##########################################################################
# Class S3QuestionTypeMultiOptionWidget
##########################################################################
class S3QuestionTypeMultiOptionWidget(S3QuestionTypeOptionWidget):
    """
        Multi Option Question Type widget

        provides a widget for the survey module that will manage options
        questions, where more than one answer can be provided.

        Available metadata for this class:
        Help message: A message to help with completing the question

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeOptionWidget.__init__(self, question_id)
        self.selectionInstructions = "Type x to mark box. Select all applicable options"
        self.typeDescription = T("Multi-Option")

    def display(self, **attr):
        S3QuestionTypeAbstractWidget.initDisplay(self, **attr)
        self.field.requires = IS_IN_SET(self.getList())
        value = self.getAnswer()
        try:
            answer = unescape(value, {"'": '"'})
            valueList = json.loads(answer)
        except json.JSONDecodeError:
            valueList = []
        self.field.name = self.question.code
        input = CheckboxesWidget.widget(self.field, valueList, **self.attr)
        self.field.name = "value"
        return self.layout(self.question.name, input, **attr)

##########################################################################
# Class S3QuestionTypeLocationWidget
##########################################################################
class S3QuestionTypeLocationWidget(S3QuestionTypeAbstractWidget):
    """
        Location widget: Question Type widget

        provides a widget for the survey module that will link to the 
        gis_locaton table, and provide the record if a match exists.

        Available metadata for this class:
        Help message: A message to help with completing the question
        Hierarchy: If the hierarchy value is set then extra questions will be
                   displayed. These relate to the following json values:
                    * Country - L0
                    * Province - L1
                    * District - L2
                    * Community - (any of L1-L5)
                    * alternative - (local or commonly used name)
                    * Latitude
                    * Longitude
                   It will use deployment_settings.gis.location_hierarchy
        Parent:    Indicates which question is used to indicate the parent
                   This is used as a simplified Hierarchy.


        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        self.typeDescription = T("Location")
        # @todo:  modify so that the metdata can define which bits are displayed
        settings = current.deployment_settings
        self.hierarchyElements = [str(settings.gis.location_hierarchy["L0"]),
                                 str(settings.gis.location_hierarchy["L1"]),
                                 str(settings.gis.location_hierarchy["L2"]),
                                 str(settings.gis.location_hierarchy["L3"]),
                                 str(settings.gis.location_hierarchy["L4"]),
                                 "Latitude",
                                 "Longitude",
                                ]
        self.hierarchyAnswers = ["L0",
                                 "L1",
                                 "L2",
                                 "L3",
                                 "L4",
                                 "Latitude",
                                 "Longitude",
                                ]
        self.locationLabel = self.hierarchyAnswers[0:-2]

    def getAnswer(self):
        """
            Return the value of the answer for this question
            
            Overloaded method.
            
            The answer can either be stored as a plain text or as a JSON string
            
            If it is plain text then this is the location as entered, and is
            the value that needs to be returned.
            
            If it is a JSON value then it should include the raw value and
            any other of the following properties.
            {'raw':'original value',
             'id':numerical value referencing a record on gis_location table,
             'alternative':'alternative name for location',
             'parent':'name of the parent location'
             'L0':L0 Name
             'L1':L1 Name
             'L2':L2 Name
             'L3':L3 Name
             'L4':L4 Name
             'Latitude':numeric
             'Longitude':numeric
            }
        """
        if "answer" in self.question:
            answer = self.question.answer
            # if it is JSON then ensure all quotes are converted to double
            try:
                rowList = self.getAnswerListFromJSON(answer)
                return rowList["raw"]
            except:
                return answer
        else:
            return ""

    def repr(self, value=None):
        """
            function to format the answer, which can be passed in
        """
        if value == None:
            return self.getAnswer()
        try:
            rowList = self.getAnswerListFromJSON(value)
            return rowList["raw"]
        except:
            return value

    def display(self, **attr):
        """
            This displays the widget on a web form. It uses the layout
            function to control how the widget is displayed
        """
        hierarchy = self.get("Hierarchy")
        if hierarchy == None:
            return S3QuestionTypeAbstractWidget.display(self, **attr)
        self.initDisplay(**attr)
        try:
            fullAnswer = self.getAnswerListFromJSON(self.question.answer)
        except:
            fullAnswer = {"L4":self.getAnswer()}
        if not isinstance(fullAnswer, dict):
            fullAnswer = {"L4":fullAnswer}
        table = TABLE()
        cnt = 0
        for element in self.hierarchyAnswers:
            if element in fullAnswer:
                value = fullAnswer[element]
            else:
                value = ""
            qstnCode = "%s(%s)" % (self.question.code,element)
            self.attr["_name"] = qstnCode
            input = self.webwidget.widget(self.field, value, **self.attr)
            table.append(self.layout(self.hierarchyElements[cnt], input,
                                     **attr))
            cnt += 1
        return self.layout(self.question.name, table, **attr)

    def getLocationRecord(self, complete_id, answer):
        """
            Return the location record from the database
        """
        record = Storage()
        if answer != None:
            gtable = current.db.gis_location
            # if it is JSON then ensure all quotes are converted to double
            try:
                rowList = self.getAnswerListFromJSON(answer)
            except:
                query = (gtable.name == answer)
                record.key = answer
            else:
                if "id" in rowList:
                    query = (gtable.id == rowList["id"])
                    record.key = rowList["id"]
                else:
                    (query, record) = self.buildQuery(rowList)
            record.result = current.db(query).select(gtable.name,
                                             gtable.lat,
                                             gtable.lon,
                                            )
            record.complete_id = complete_id
            if len(record.result) == 0:
                msg = "Unknown Location %s, %s, %s" % \
                            (answer, query, record.key)
                _debug(msg)
            return record
        else:
            return None

    def parseForm(self, vars, code):
        """
            Get the location hierarchy data from the different html input tags
            and merge them into a JSON string to be saved in survey_answer  
        """
        hierarchy = self.get("Hierarchy")
        answerList = {}
        if hierarchy != None:
            for element in self.hierarchyAnswers:
                index = "%s(%s)" % (code,element)
                if index in vars and vars[index] != "":
                    answerList[element] = vars[index]
            jsonAnswer = json.dumps(answerList)
            jsonValue = unescape(jsonAnswer, {'"': "'"})
            return jsonValue
        return None
            

    def onaccept(self, value):
        """
            Method to format the value that has just been put on the database

            If the value is a json then data might need to be extracted from it
            
        """
        try:
            answerList = self.getAnswerListFromJSON(value)
        except:
            return value
        newValue = {}
        hierarchy = self.get("Hierarchy")
        if hierarchy != None:
            prevLocation = ""
            lastLocation = ""
            for element in self.hierarchyAnswers:
                if element in answerList:
                    newValue[element] = answerList[element]
                    if element in self.locationLabel:
                        prevLocation = lastLocation
                        lastLocation = answerList[element]
                        # @todo: need to see if gis_location exists if NOT add
            # @todo: may need to add/update lat & lon to last location
            newValue["raw"] = lastLocation
            newValue["parent"] = prevLocation
        jsonAnswer = json.dumps(newValue)
        jsonValue = unescape(jsonAnswer, {'"': "'"})
        return jsonValue

    def buildQuery(self, rowList):
        """
            Function that will build a gis_location query
            
            @todo: Extend this to test the L0-L4 values 
        """
        db = current.db
        record = Storage()
        gtable = db.gis_location
        if "alternative" in rowList:
            query = (gtable.name == rowList["alternative"])
            record.key = rowList["alternative"]
        else:
            query = (gtable.name == rowList["raw"])
            record.key = rowList["raw"]
        if "Parent" in rowList:
            q = gtable.name == rowList["Parent"]
            parent_query = db(q).select(gtable.id)
            query = query & (gtable.parent.belongs(parent_query))
            record.key += rowList["Parent"]
        return (query, record)

    def getAnswerListFromJSON(self, answer):
        """
            If the answer is stored as a JSON value return the data as a map

            If it is not valid JSON then an exception will be raised,
            and must be handled by the calling function
        """
        jsonAnswer = unescape(answer, {"u'": '"'})
        jsonAnswer = unescape(jsonAnswer, {"'": '"'})
        return json.loads(jsonAnswer)

    def writeToMatrix(self,
                      matrix, 
                      row,
                      col,
                      langDict=dict(),
                      answerMatrix=None,
                      style={"Label": True
                            ,"LabelLeft" : True
                            },
                      ):
        """
            Function to write out basic details to the matrix object
        """
        self._store_metadata()
        hierarchy = self.get("Hierarchy")
        if hierarchy == None:
            return S3QuestionTypeAbstractWidget.writeToMatrix(self,
                                                              matrix,
                                                              row,
                                                              col,
                                                              langDict,
                                                              answerMatrix,
                                                              style)
        # The full hierarchy needs to be provided
        # First display the question as a subtitle
        cell = MatrixElement(row,
                             col,
                             self._Tquestion(langDict),
                             style="styleSubHeader"
                            )
        matrix.addElement(cell)
        row += 1
        answerPosn = 3
        originalCol = col
        if answerMatrix != None:
            answerRow = answerMatrix.lastRow+1
            cell = MatrixElement(answerRow,
                                 0,
                                 self.question["code"],
                                 style="styleSubHeader"
                                )
            answerMatrix.addElement(cell)
            cell = MatrixElement(answerRow,
                                 1,
                                 len(self.hierarchyAnswers),
                                 style="styleSubHeader"
                                )
            answerMatrix.addElement(cell)
            cell = MatrixElement(answerRow,
                                 2,
                                 "|#|".join(self.hierarchyAnswers),
                                 style="styleSubHeader"
                                 )
            answerMatrix.addElement(cell)
        for value in self.hierarchyElements:
            col = originalCol
            if "Label" in style and style["Label"]:
                cell = MatrixElement(row,
                                     col,
                                     survey_T(str(value), langDict),
                                     style="styleSubHeader"
                                    )
                matrix.addElement(cell)
                if "LabelLeft" in style and style["LabelLeft"]:
                    col += 1
                else:
                    row += 1
            cell = MatrixElement(row,
                                 col,
                                 "",
                                 style="styleInput"
                                )
            matrix.addElement(cell)
            if answerMatrix != None:
                cell = MatrixElement(answerRow,
                                     answerPosn,
                                     self.rowcol_to_cell(row, col),
                                     style="styleText"
                                    )
                answerMatrix.addElement(cell)
                answerPosn += 1
            row += 1
        return (row+1, col+1)

    ######################################################################
    # Functions not fully implemented or used
    ######################################################################
    def validate(self, valueList, qstn_id):
        """
            This will validate the data passed in to the widget
        """
        result = S3QuestionTypeAbstractWidget.validate(self, valueList)
        if result != ANSWER_VALID:
            return result
        length = self.get("length", 10)
        format = self.get("format")
        data = value(valueList, 0)
        if format != None:
            try:
                self.formattedValue(data, format)
                return self.ANSWER_VALID
            except exceptions.ValueError:
                return self.ANSWER_INVALID

        return self.ANSWER_VALID


##########################################################################
# Class S3QuestionTypeLinkWidget
##########################################################################
class S3QuestionTypeLinkWidget(S3QuestionTypeAbstractWidget):
    """
        Link widget: Question Type widget

        provides a widget for the survey module that has a link with another
        question.

        Available metadata for this class:
        Help message: A message to help with completing the question
        Parent: The question it links to
        Type: The type of question it really is (another question type)
        Relation: How it relates to the parent question
                  groupby: answers should be grouped by the value of the parent

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        self.metalist.append("Parent")
        self.metalist.append("Type")
        self.metalist.append("Relation")
        try:
            self._store_metadata()
            type = self.get("Type")
            parent = self.get("Parent")
            if type == None or parent == None:
                self.typeDescription = T("Link")
            else:
                self.typeDescription = T("%s linked to %s") % (type, parent)
        except:
            self.typeDescription = T("Link") 

    def display(self, **attr):
        type = self.get("Type")
        realWidget = survey_question_type[type]()
        realWidget.question = self.question
        realWidget.qstn_metadata = self.qstn_metadata
        return realWidget.display(**attr)

    def onaccept(self, value):
        """
            Method to format the value that has just been put on the database
        """
        type = self.get("Type")
        realWidget = survey_question_type[type]()
        return realWidget.onaccept(value)

    def getParentType(self):
        self._store_metadata()
        return self.get("Type")

    def getParentQstnID(self):
        db = current.db
        parent = self.get("Parent")
        query = (self.qtable.code == parent)
        row = db(query).select(limitby=(0, 1)).first()
        return row.id

    def fullName(self):
        return self.question.name

    ######################################################################
    # Functions not fully implemented or used
    ######################################################################
    def validate(self, valueList, qstn_id):
        """
            This will validate the data passed in to the widget
        """
        result = S3QuestionTypeAbstractWidget.validate(self, valueList)
        type = self.get("Type")
        realWidget = survey_question_type[type]()
        return realWidget.validate(valueList, qstn_id)

##########################################################################
# Class S3QuestionTypeGridWidget
##########################################################################
class S3QuestionTypeGridWidget(S3QuestionTypeAbstractWidget):
    """
        Grid widget: Question Type widget

        provides a widget for the survey module that hold a grid of related 
        questions.

        Available metadata for this class:
        Help message: A message to help with completing the question
        Subtitle: The text for the 1st column and 1st row of the grid
        QuestionNo: The number of the first question, used for the question code
        col-cnt:  The number of data columns in the grid
        row-cnt:  The number of data rows in the grid
        columns:  An array of headings for each data column
        rows:     An array of headings for each data row
        data:     A matrix of widgets for each data cell

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        self.metalist.append("Subtitle")
        self.metalist.append("QuestionNo")
        self.metalist.append("col-cnt")
        self.metalist.append("row-cnt")
        self.metalist.append("columns")
        self.metalist.append("rows")
        self.metalist.append("data")
        self.typeDescription = T("Grid")

    def getMetaData(self, qstn_id=None):
        self._store_metadata(qstn_id=qstn_id, update=True)
        self.subtitle = self.get("Subtitle")
        self.qstnNo = int(self.get("QuestionNo", 1))
        self.colCnt = self.get("col-cnt")
        self.rowCnt = self.get("row-cnt")
        self.columns = json.loads(self.get("columns"))
        self.rows = json.loads(self.get("rows"))
        self.data = json.loads(self.get("data"))

    def getHeading(self, number):
        self.getMetaData()
        col = (number - self.qstnNo) % int(self.colCnt)
        return self.columns[col]

    def display(self, **attr):
        S3QuestionTypeAbstractWidget.display(self, **attr)
        complete_id = None
        if "complete_id" in self.question:
            complete_id = self.question.complete_id
        self.getMetaData()
        table = []
        if self.data != None:
            tr = TR(_class="survey_question")
            tr.append(TH(self.subtitle))
            for col in self.columns:
                tr.append(TH(col))
            table.append(tr)
            posn = 0
            codeNum = self.qstnNo
            for row in self.data:
                tr = TR(_class="survey_question")
                tr.append(TH(self.rows[posn]))
                for cell in row:
                    if cell == "Blank":
                        tr.append("")
                    else:
                        code = "%s%s" % (self.question["code"], codeNum)
                        codeNum += 1
                        childWidget = self.getChildWidget(code)
                        if complete_id != None:
                            childWidget.loadAnswer(complete_id,
                                                   childWidget.id)
                        tr.append(childWidget.subDisplay())
                table.append(tr)
                posn += 1
        return table

    def writeToMatrix(self,
                      matrix,
                      row,
                      col,
                      langDict=dict(),
                      answerMatrix=None,
                      style={"Label": True
                            ,"LabelLeft" : True
                            }
                      ):
        """
            Function to write out basic details to the matrix object
        """
        self._store_metadata()
        self.getMetaData()
        startcol = col
        nextrow = row
        nextcol = col
        gridStyle = style
        gridStyle["Label"] = False
        if self.data != None:
            cell = MatrixElement(row, col, survey_T(self.subtitle, langDict),
                                 style="styleSubHeader")
            matrix.addElement(cell)
            # Add a *mostly* blank line for the heading.
            # This will be added on the first run through the list
            # To take into account the number of columns required
            firstRun = True
            colCnt = 0
            nextrow += 1
            posn = 0
            codeNum = self.qstnNo
            for line in self.data:
                col = startcol
                row = nextrow
                cell = MatrixElement(row, col, survey_T(self.rows[posn],
                                                        langDict),
                                     style="styleText")
                matrix.addElement(cell)
                col += 1
                for cell in line:
                    if firstRun:
                        cell = MatrixElement(row - 1, col,
                                             survey_T(self.columns[colCnt],
                                                      langDict),
                                             style="styleSubHeader")
                        matrix.addElement(cell)
                        colCnt += 1
                    if cell == "Blank":
                        col += 1
                    else:
                        code = "%s%s" % (self.question["code"], codeNum)
                        codeNum += 1
                        childWidget = self.getChildWidget(code)
                        type = childWidget.get("Type")
                        realWidget = survey_question_type[type](childWidget.id)
                        (endrow, col) = realWidget.writeToMatrix(matrix,
                                                                 row,
                                                                 col, 
                                                                 langDict,
                                                                 answerMatrix,
                                                                 style)
                    if endrow > nextrow:
                        nextrow = endrow
                posn += 1
                if col > nextcol:
                    nextcol = col
                firstRun = False
        return (nextrow+1, nextcol)


    def insertChildren(self, record, metadata):
        self.id = record.id
        self.question = record
        self.qstn_metadata = metadata
        self.getMetaData()
        if self.data != None:
            posn = 0
            qstnNo = self.qstnNo
            parent_id = self.id
            parent_code = self.question["code"]
            for row in self.data:
                name = self.rows[posn]
                posn += 1
                for cell in row:
                    if cell == "Blank":
                        continue
                    else:
                        type = cell
                        code = "%s%s" % (parent_code, qstnNo)
                        qstnNo += 1
                        childMetadata = self.get(code)
                        if childMetadata == None:
                            childMetadata = {}
                        else:
                            childMetadata = json.loads(childMetadata)
                        childMetadata["Type"] = type
                        # web2py stomps all over a list so convert back to a string
                        # before inserting it on the database
                        metadata = json.dumps(childMetadata)
                        try:
                            id = self.qtable.insert(name = name,
                                                    code = code,
                                                    type = "GridChild",
                                                    metadata = metadata,
                                                   )
                        except:
                            record = self.qtable(code = code)
                            id = record.id
                            record.update_record(name = name,
                                                 code = code,
                                                 type = "GridChild",
                                                 metadata = metadata,
                                                )
                        record = self.qtable(id)
                        current.manager.s3.survey_updateMetaData(record,
                                                                 "GridChild",
                                                                 childMetadata)

    def insertChildrenToList(self, question_id, template_id, section_id,
                             qstn_posn):
        self.getMetaData(question_id)
        if self.data != None:
            posn = 0
            qstnNo = self.qstnNo
            qstnPosn = 1
            parent_id = self.id
            parent_code = self.question["code"]
            for row in self.data:
                name = self.rows[posn]
                posn += 1
                for cell in row:
                    if cell == "Blank":
                        continue
                    else:
                        code = "%s%s" % (parent_code, qstnNo)
                        qstnNo += 1
                        record = self.qtable(code = code)
                        id = record.id
                        try:
                            self.qltable.insert(question_id = id,
                                                template_id = template_id,
                                                section_id = section_id,
                                                posn = qstn_posn+qstnPosn,
                                               )
                            qstnPosn += 1
                        except:
                            pass # already on the database no change required
        
    def getChildWidget (self, code):
            # Get the question from the database
            query = (self.qtable.code == code)
            question = current.db(query).select(limitby=(0, 1)).first()
            if question == None:
                raise Exception("no question with code %s in database" % code)
            cellWidget = survey_question_type["GridChild"](question.id)
            return cellWidget

##########################################################################
# Class S3QuestionTypeGridChildWidget
##########################################################################
class S3QuestionTypeGridChildWidget(S3QuestionTypeAbstractWidget):
    """
        GridChild widget: Question Type widget

        provides a widget for the survey module that is held by a grid question
        type an provides a link to the true question type.

        Available metadata for this class:
        Type:     The type of question it really is (another question type)

        @author: Graeme Foster (graeme at acm dot org)
    """
    def __init__(self,
                 question_id = None
                ):
        T = current.T
        S3QuestionTypeAbstractWidget.__init__(self, question_id)
        if self.question != None and "code" in self.question:
            # Expect the parent code to be the same as the child with the number
            # removed. This means that the parent code must end with a hyphen.
            end = self.question.code.rfind("-")+1
            parentCode = self.question.code[0:end]
            parentNumber = self.question.code[end:]
            self.question.parentCode = parentCode
            self.question.parentNumber = int(parentNumber)
        self.metalist.append("Type")
        self.typeDescription = T("Grid Child")

    def display(self, **attr):
        return None

    def fullName(self):
        if "parentCode" in self.question:
            db = current.db
            query = db(self.qtable.code == self.question.parentCode)
            record = query.select(self.qtable.id,
                                  self.qtable.name,
                                  limitby=(0, 1)).first()
            if record != None:
                parentWidget = survey_question_type["Grid"](record.id)
                subHeading = parentWidget.getHeading(self.question.parentNumber)
                return "%s - %s (%s)" % (record.name,
                                         self.question.name,
                                         subHeading)
        return self.question.name

    def subDisplay(self, **attr):
        S3QuestionTypeAbstractWidget.display(self, **attr)
        type = self.get("Type")
        realWidget = survey_question_type[type]()
        realWidget.question = self.question
        realWidget.qstn_metadata = self.qstn_metadata
        return realWidget.display(question_id=self.id, display="Control Only")

    def getParentType(self):
        self._store_metadata()
        return self.get("Type")

    def writeToMatrix(self,
                      matrix,
                      row,
                      col,
                      langDict=dict(),
                      answerMatrix=None,
                      style={}
                     ):
        """
            Dummy function that doesn't write anything to the matrix, 
            because it is handled by the Grid question type
        """
        return (row, col)


###############################################################################
###  Classes for analysis
###    will work with a list of answers for the same question
###############################################################################

# Analysis Types
def analysis_stringType(question_id, answerList):
    return S3StringAnalysis("String", question_id, answerList)
def analysis_textType(question_id, answerList):
    return S3TextAnalysis("Text", question_id, answerList)
def analysis_numericType(question_id, answerList):
    return S3NumericAnalysis("Numeric", question_id, answerList)
def analysis_dateType(question_id, answerList):
    return S3DateAnalysis("Date", question_id, answerList)
def analysis_optionType(question_id, answerList):
    return S3OptionAnalysis("Option", question_id, answerList)
def analysis_ynType(question_id, answerList):
    return S3OptionYNAnalysis("YesNo", question_id, answerList)
def analysis_yndType(question_id, answerList):
    return S3OptionYNDAnalysis("YesNoDontKnow", question_id, answerList)
def analysis_optionOtherType(question_id, answerList):
    return S3OptionOtherAnalysis("OptionOther", question_id, answerList)
def analysis_multiOptionType(question_id, answerList):
    return S3MultiOptionAnalysis("MultiOption", question_id, answerList)
def analysis_locationType(question_id, answerList):
    return S3LocationAnalysis("Location", question_id, answerList)
def analysis_linkType(question_id, answerList):
    return S3LinkAnalysis("Link", question_id, answerList)
def analysis_gridType(question_id, answerList):
    return S3GridAnalysis("Grid", question_id, answerList)
def analysis_gridChildType(question_id, answerList):
    return S3GridChildAnalysis("GridChild", question_id, answerList)
#def analysis_ratingType(answerList):
#    return S3RatingAnalysis(answerList)
#    pass

survey_analysis_type = {
    "String": analysis_stringType,
    "Text": analysis_textType,
    "Numeric": analysis_numericType,
    "Date": analysis_dateType,
    "Option": analysis_optionType,
    "YesNo": analysis_ynType,
    "YesNoDontKnow": analysis_yndType,
    "OptionOther": analysis_optionOtherType,
    "MultiOption" : analysis_multiOptionType,
    "Location": analysis_locationType,
    "Link": analysis_linkType,
    "Grid": analysis_gridType,
    "GridChild" : analysis_gridChildType,
#    "Rating": analysis_ratingType,
}

# -----------------------------------------------------------------------------
class S3AnalysisPriority():
    def __init__(self,
                 range=[-1, -0.5, 0, 0.5, 1],
                 colour={-1:"#888888", # grey
                          0:"#000080", # blue
                          1:"#008000", # green
                          2:"#FFFF00", # yellow
                          3:"#FFA500", # orange
                          4:"#FF0000", # red
                          5:"#880088", # purple
                        },
                 image={-1:"grey", 
                          0:"blue", 
                          1:"green", 
                          2:"yellow", 
                          3:"orange", 
                          4:"red",
                          5:"purple",
                        },
                 desc={-1:"No Data", 
                          0:"Very Low", 
                          1:"Low", 
                          2:"Medium Low", 
                          3:"Medium High", 
                          4:"High",
                          5:"Very High",
                        },
                 zero = True
                 ):
        self.range = range
        self.colour = colour
        self.image = image
        self.description = desc

    def imageURL(self, app, key):
        T = current.T
        base_url = "/%s/static/img/survey/" % app
        dot_url = base_url + "%s-dot.png" %self.image[key]
        image = IMG(_src=dot_url,
                    _alt=T(self.image[key]),
                    _height=12,
                    _width=12,
                   )
        return image

    def desc(self, key):
        T = current.T
        return T(self.description[key])

    def rangeText(self, key, pBand):
        T = current.T
        if key == -1:
            return ""
        elif key == 0:
            return T("At or below %s" % (pBand[1]))
        elif key == len(pBand)-1:
            return T("Above %s" % (pBand[len(pBand)-1]))
        else:
            return "%s - %s" % (pBand[key], pBand[key+1])

# -----------------------------------------------------------------------------
class S3AbstractAnalysis():
    """
        Abstract class used to hold all the responses for a single question
        and perform some simple analysis on the data.
        
        This class holds the main functions for:
         * displaying tables of results
         * displaying charts
         * grouping the data.

        Properties
        ==========
        question_id    - The id from the database
        answerList     - A list of answers, taken from the survey_answer
                         id, complete_id and value
                         See models/survey.py getAllAnswersForQuestionInSeries() 
        valueList      - A list of validated & sanitised values 
        result         - A list of results before formatting
        type           - The question type
        qstnWidget     - The question Widget for this question
        priorityGroup  - The type of priority group to use in the map
        priorityGroups - The priority data used to colour the markers on the map
    """
    def __init__(self,
                 type,
                 question_id,
                 answerList,
                ):
        self.question_id = question_id
        self.answerList = answerList
        self.valueList = []
        self.result = []
        self.type = type
        self.qstnWidget = survey_question_type[self.type](question_id = question_id)
        self.priorityGroup = "zero" # Ensures that it doesn't go negative
        self.priorityGroups = {"default" : [-1, -0.5, 0, 0.5, 1],
                               "standard" : [-2, -1, 0, 1, 2],
                               }
        for answer in self.answerList:
            if self.valid(answer):
                try:
                    cast = self.castRawAnswer(answer["complete_id"],
                                              answer["value"])
                    if cast != None:
                        self.valueList.append(cast)
                except:
                    if DEBUG:
                        raise
                    pass
        
        self.basicResults()

    def valid(self, answer):
        """
            used to validate a single answer
        """
        # @todo add validation here
        # widget = S3QuestionTypeNumericWidget()
        # widget.validate(answer)
        # if widget.ANSWER_VALID:
        return True

    def castRawAnswer(self, complete_id, answer):
        """
            Used to modify the answer from its raw text format.
            Where necessary, this will function be overridden.
        """
        return answer

    def basicResults(self):
        """
            Perform basic analysis of the answer set.
            Where necessary, this will function be overridden.
        """
        pass

    def chartButton(self, series_id):
        """
            This will display a button which when pressed will display a chart
            When a chart is not appropriate then the subclass will override this
            function with a nul function.
        """
        if len(self.valueList) == 0:
            return None
        if series_id == None:
            return None
        src = URL(r=current.request,
                  f="completed_chart",
                  vars={"question_id":self.question_id,
                        "series_id" : series_id,
                        "type" : self.type
                        }
                 )
        link = A(current.T("Chart"), _href=src, _target="blank",
                 _class="action-btn")
        return DIV(link, _class="surveyChart%sWidget" % self.type)

    def drawChart(self, output=None, data=None, label=None,
                  xLabel=None, yLabel=None):
        """
            This function will draw the chart using the answer set.
            
            This function must be overridden by the subclass.
        """
        msg = "Programming Error: No chart for %sWidget" % self.type
        output = StringIO()
        output.write(msg)
        current.response.body = output

    def summary(self):
        """
            Calculate a summary of basic data.
            
            Where necessary, this will function be overridden.
        """
        self.result = []
        return self.count()

    def count(self):
        """
            Create a basic count of the data set.
            
            Where necessary, this will function be overridden.
        """
        self.result.append(([current.T("Replies")], len(self.answerList))) 
        return self.format()
    
    def format(self):
        """
            This function will take the results and present them in a HTML table
        """
        table = TABLE()
        for (key, value) in self.result:
            table.append(TR(TD(B(key)), TD(value)))
        return table

    def uniqueCount(self):
        """
            Calculate the number of occurances of each value
        """
        map = {}
        for answer in self.valueList:
            if answer in map:
                map[answer] += 1
            else:
                map[answer] = 1
        return map

    def groupData(self, groupAnswer):
        """
            method to group the answers by the categories passed in
            The categories will belong to another question.
            
            For example the categories might be an option question which has 
            responses from High, Medium and Low. So all the responses that
            correspond to the High category will go into one group, the Medium
            into a second group and Low into the final group.
            
            Later these may go through a filter which could calculate the
            sum, or maybe the mean. Finally the result will be split.
            
            See controllers/survey.py - series_graph() 
        """
        grouped = {}
        answers = {}
        for answer in self.answerList:
            # hold the raw value (filter() will pass the value through castRawAnswer()
            answers[answer["complete_id"]] = answer["value"]
        # Step through each of the responses on the categories question
        for ganswer in groupAnswer:
            gcode = ganswer["complete_id"]
            greply = ganswer["value"]
            # If response to the group question also has a response to the main question
            # Then store the response in value, otherwise return an empty list for this response
            if gcode in answers:
                value = answers[gcode]
                if greply in grouped:
                    grouped[greply].append(value)
                else:
                    grouped[greply] = [value]
            else:
                if greply not in grouped:
                    grouped[greply] = []
        return grouped

    def filter(self, filterType, groupedData):
        """
            Filter the data within the groups by the filter type
        """
        return groupedData

    def splitGroupedData(self, groupedData):
        """
            Split the data set by the groups
        """
        keys = []
        values = []
        for (key, value) in groupedData.items():
            keys.append(key)
            values.append(value)
        return (keys, values)

# -----------------------------------------------------------------------------
class S3StringAnalysis(S3AbstractAnalysis):

    def chartButton(self, series_id):
        return None

# -----------------------------------------------------------------------------
class S3TextAnalysis(S3AbstractAnalysis):

    def chartButton(self, series_id):
        return None

# -----------------------------------------------------------------------------
class S3DateAnalysis(S3AbstractAnalysis):

    def chartButton(self, series_id):
        return None


# -----------------------------------------------------------------------------
class S3NumericAnalysis(S3AbstractAnalysis):

    def __init__(self,
                 type,
                 question_id,
                 answerList
                ):
        S3AbstractAnalysis.__init__(self, type, question_id, answerList)
        self.histCutoff = 10

    def castRawAnswer(self, complete_id, answer):
        try:
            return float(answer)
        except:
            return None

    def summary(self):
        T = current.T
        widget = S3QuestionTypeNumericWidget()
        fmt = widget.formattedAnswer
        if self.sum:
            self.result.append(([T("Total")], fmt(self.sum)))
        if self.average:
            self.result.append(([T("Average")], fmt(self.average)))
        if self.max:
            self.result.append(([T("Maximum")], fmt(self.max)))
        if self.min:
            self.result.append(([T("Minimum")], fmt(self.min)))
        return self.format()

    def count(self):
        T = current.T
        self.result.append((T("Replies"), len(self.answerList)))
        self.result.append((T("Valid"), self.cnt))
        return self.format()

    def basicResults(self):
        self.cnt = 0
        if len(self.valueList) == 0:
            self.sum = None
            self.average = None
            self.max = None
            self.min = None
            return
        self.sum = 0
        self.max = self.valueList[0]
        self.min = self.valueList[0]
        for answer in self.valueList:
            self.cnt += 1
            self.sum += answer
            if answer > self.max:
                self.max = answer
            if answer < self.min:
                self.min = answer
        self.average = self.sum / float(self.cnt)

    def advancedResults(self):
        try:
            from numpy import array
        except:
            print >> sys.stderr, "ERROR: S3Survey requires numpy library installed."

        array = array(self.valueList)
        self.std = array.std()
        self.mean = array.mean()
        self.zscore = {}
        for answer in self.answerList:
            complete_id = answer["complete_id"]
            try:
                value = self.castRawAnswer(complete_id, answer["value"])
            except:
                continue
            if value != None:
                self.zscore[complete_id] = (value - self.mean) / self.std

    def priority(self, complete_id, priorityObj):
        priorityList = priorityObj.range
        priority = 0
        try:
            zscore = self.zscore[complete_id]
            for limit in priorityList:
                if zscore <= limit:
                    return priority
                priority += 1
            return priority
        except:
            return -1

    def priorityBand(self, priorityObj):
        priorityList = priorityObj.range
        priority = 0
        band = [""]
        for limit in priorityList:
            band.append(int(self.mean + limit * self.std))
        return band

    def chartButton(self, series_id):
        if len(self.valueList) < self.histCutoff:
            return None
        return S3AbstractAnalysis.chartButton(self, series_id)

    def drawChart(self, output="xml",
                  data=None, label=None, xLabel=None, yLabel=None):
        chart = current.chart()
        chart.displayAsIntegers()
        if data == None:
            chart.survey_hist(self.qstnWidget.question.name,
                              self.valueList,
                              10,
                              0,
                              self.max,
                              xlabel = self.qstnWidget.question.name,
                              ylabel = current.T("Count")
                             )
        else:
            chart.survey_bar(self.qstnWidget.question.name,
                             data,
                             label,
                             []
                            )
        image = chart.draw(output=output)
        return image

    def filter(self, filterType, groupedData):
        filteredData = {}
        if filterType == "Sum":
            for (key, valueList) in groupedData.items():
                sum = 0
                for value in valueList:
                    try:
                        sum += self.castRawAnswer(None, value)
                    except:
                        pass
                filteredData[key] = sum
            return filteredData
        return groupedData


# -----------------------------------------------------------------------------
class S3OptionAnalysis(S3AbstractAnalysis):

    def summary(self):
        T = current.T
        for (key, value) in self.listp.items():
            self.result.append((T(key), value))
        return self.format()

    def basicResults(self):
        self.cnt = 0
        self.list = {}
        for answer in self.valueList:
            self.cnt += 1
            if answer in self.list:
                self.list[answer] += 1
            else:
                self.list[answer] = 1
        self.listp = {}
        if self.cnt != 0:
            for (key, value) in self.list.items():
                self.listp[key] = "%3.1f%%" % \
                    round((100.0 * value) / self.cnt, 1)

    def drawChart(self, output="xml",
                  data=None, label=None, xLabel=None, yLabel=None):
        data = []
        label = []
        for (key, value) in self.list.items():
            data.append(value)
            label.append(key)
        chart = current.chart()
        chart.survey_pie(self.qstnWidget.question.name,
                         data,
                         label)
        image = chart.draw(output=output)
        return image

# -----------------------------------------------------------------------------
class S3OptionYNAnalysis(S3OptionAnalysis):
    def summary(self):
        T = current.T
        self.result.append((T("Yes"), self.yesp))
        self.result.append((T("No"), self.nop))
        return self.format()


    def basicResults(self):
        S3OptionAnalysis.basicResults(self)
        T = current.T
        if "Yes" in self.listp:
            self.yesp = self.listp["Yes"]
        else:
            if self.cnt == 0:
                self.yesp = "" # No replies so can't give a percentage
            else:
                self.list["Yes"] = 0
                self.yesp = T("0%")
        if "No" in self.listp:
            self.nop = self.listp["No"]
        else:
            if self.cnt == 0:
                self.nop =  "" # No replies so can't give a percentage
            else:
                self.list["No"] = 0
                self.nop = T("0%")

# -----------------------------------------------------------------------------
class S3OptionYNDAnalysis(S3OptionAnalysis):
    def summary(self):
        T = current.T
        self.result.append((T("Yes"), self.yesp))
        self.result.append((T("No"), self.nop))
        self.result.append((T("Don't Know"), self.dkp))
        return self.format()

    def basicResults(self):
        S3OptionAnalysis.basicResults(self)
        T = current.T
        if "Yes" in self.listp:
            self.yesp = self.listp["Yes"]
        else:
            if self.cnt == 0:
                self.yesp = "" # No replies so can't give a percentage
            else:
                self.list["Yes"] = 0
                self.yesp = T("0%")
        if "No" in self.listp:
            self.nop = self.listp["No"]
        else:
            if self.cnt == 0:
                self.nop = "" # No replies so can't give a percentage
            else:
                self.list["No"] = 0
                self.nop = T("0%")
        if "Don't Know" in self.listp:
            self.dkp = self.listp["Don't Know"]
        else:
            if self.cnt == 0:
                self.dkp = "" # No replies so can't give a percentage
            else:
                self.list["Don't Know"] = 0
                self.dkp = T("0%")

# -----------------------------------------------------------------------------
class S3OptionOtherAnalysis(S3OptionAnalysis):
    pass

# -----------------------------------------------------------------------------
class S3MultiOptionAnalysis(S3OptionAnalysis):

#    def __init__(self,
#                 type,
#                 question_id,
#                 answerList
#                ):
#        newList = []
#        for answer in answerList:
#            try:
#                value = unescape(answer, {"'": '"'})
#                valueList = json.loads(answer)
#            except json.JSONDecodeError:
#                valueList = []
#            newList.append(valueList)
#        S3AbstractAnalysis.__init__(self, type, question_id, newList)

    def castRawAnswer(self, complete_id, answer):
        """
            Used to modify the answer from its raw text format.
            Where necessary, this will function be overridden.
        """
        try:
            value = unescape(answer, {"'": '"'})
            valueList = json.loads(value)
        except json.JSONDecodeError:
            valueList = []
        return valueList

    def basicResults(self):
        self.cnt = 0
        self.list = {}
        for answer in self.valueList:
            if isinstance(answer, list):
                answerList = answer
            else:
                answerList = [answer]
            self.cnt += 1
            for answer in answerList:
                if answer in self.list:
                    self.list[answer] += 1
                else:
                    self.list[answer] = 1
        self.listp = {}
        if self.cnt != 0:
            for (key, value) in self.list.items():
                self.listp[key] = "%s%%" %((100 * value) / self.cnt)

    def drawChart(self, output="xml",
                  data=None, label=None, xLabel=None, yLabel=None):
        data = []
        label = []
        for (key, value) in self.list.items():
            data.append(value)
            label.append(key)
        chart = current.chart()
        chart.survey_bar(self.qstnWidget.question.name,
                         data,
                         label,
                         None
                         )
        image = chart.draw(output=output)
        return image


# -----------------------------------------------------------------------------
class S3LocationAnalysis(S3AbstractAnalysis):
    """
        Widget for analysing Location type questions
        
        The analysis will compare the location values provided with
        data held on the gis_location table.
        
        The data held can be in its raw form (the actual value imported) or
        in a more refined state, which may include the actual location id
        held on the database or an alternative value which is a string.
        
        The raw value may be a local name for the place whilst the altervative
        value should be the actual value held on the database.
        The alternative value is useful for matching duplicate responses that
        are using the same local name.
    """
    def castRawAnswer(self, complete_id, answer):
        """
            Convert the answer for the complete_id into a database record.
            
            This can have one of three type of return values.
            A single record: The actual location
            Multiple records: The set of location, on of which is the location
            None: No match is found on the database.  
        """
        records = self.qstnWidget.getLocationRecord(complete_id, answer)
        return records

    def summary(self):
        """
            Returns a summary table
        """
        T = current.T
        self.result.append((T("Known Locations"), self.kcnt))
        self.result.append((T("Duplicate Locations"), self.dcnt))
        self.result.append((T("Unknown Locations"), self.ucnt))
        return self.format()
    
    def count(self):
        """
            Returns a table of basic results
        """
        T = current.T
        self.result.append((T("Total Locations"), len(self.valueList)))
        self.result.append((T("Unique Locations"), self.cnt))
        return self.format()

    def basicResults(self):
        """
            Calculate the basic results, which consists of a number of list
            related to the locations
            
            LISTS (dictionaries)
            ====================
            All maps are keyed on the value used in the database lookup
            locationList - holding the number of times the value exists 
            complete_id  - a list of complete_id at this location
            duplicates   - a list of duplicate records
            known        - The record from the database
            
            Calculated Values
            =================
            cnt  - The number of unique locations
            dcnt - The number of locations with duplicate values
            kcnt - The number of known locations (single match on the database)
            ucnt - The number of unknown locations
            dper - The percentage of locations with duplicate values
            kper - The percentage of known locations
            NOTE: Percentages are calculated from the unique locations
                  and not from the total responses.
        """
        self.locationList = {}
        self.duplicates = {}
        self.known = {}
        self.complete_id = {}
        for answer in self.valueList:
            if answer != None:
                if isinstance(answer, dict):
                    key = answer.key
                else:
                    key = answer
                if key in self.locationList:
                    self.locationList[key] += 1
                else:
                    self.locationList[key] = 1
                    if key in self.complete_id:
                        self.complete_id[key].append(answer.complete_id)
                    else:
                        self.complete_id[key] = [answer.complete_id]
                    result = answer.result
                    if len(result) > 1:
                        self.duplicates[key] = result
                    if len(result) == 1:
                        self.known[key] = result.first()
        self.cnt = len(self.locationList)
        self.dcnt = len(self.duplicates)
        self.kcnt = len(self.known)
        if self.cnt == 0:
            self.dper = "0%%"
            self.kper = "0%%"
        else:
            self.dper = "%s%%" %((100 * self.dcnt) / self.cnt)
            self.kper = "%s%%" %((100 * self.kcnt) / self.cnt)
        self.ucnt = self.cnt - self.kcnt - self.dcnt

    def chartButton(self, series_id):
        """
            Ensures that no button is set up
        """
        return None

    def uniqueCount(self):
        """
            Calculate the number of occurances of each value
        """
        map = {}
        for answer in self.valueList:
            if answer.key in map:
                map[answer.key] += 1
            else:
                map[answer.key] = 1
        return map

# -----------------------------------------------------------------------------
class S3LinkAnalysis(S3AbstractAnalysis):
    def __init__(self,
                 type,
                 question_id,
                 answerList
                ):
        S3AbstractAnalysis.__init__(self, type, question_id, answerList)
        linkWidget = S3QuestionTypeLinkWidget(question_id)
        parent = linkWidget.get("Parent")
        relation = linkWidget.get("Relation")
        type = linkWidget.get("Type")
        parent_qid = linkWidget.getParentQstnID()
        valueMap = {}
        for answer in self.answerList:
            complete_id = answer["complete_id"]
            parent_answer = linkWidget.loadAnswer(complete_id, parent_qid,
                                                  forceDB=True)
            if relation == "groupby":
                # @todo: check for different values
                valueMap.update({parent_answer:answer})
        valueList = [] 
        for answer in valueMap.values():
            valueList.append(answer)
        self.widget = survey_analysis_type[type](question_id, valueList)

    def summary(self):
        return self.widget.summary()
    
    def count(self):
        return self.widget.count()

    def chartButton(self, series_id):
        return self.widget.chartButton(series_id)

    def filter(self, filterType, groupedData):
        return self.widget.filter(filterType, groupedData)

    def drawChart(self, output="xml",
                  data=None, label=None, xLabel=None, yLabel=None):
        return self.widget.drawChart(data, label, xLabel, yLabel)


# -----------------------------------------------------------------------------
class S3GridAnalysis(S3AbstractAnalysis):
    pass

# -----------------------------------------------------------------------------
class S3GridChildAnalysis(S3AbstractAnalysis):
    def __init__(self,
                 type,
                 question_id,
                 answerList
                ):
        S3AbstractAnalysis.__init__(self, type, question_id, answerList)
        childWidget = S3QuestionTypeLinkWidget(question_id)
        trueType = childWidget.get("Type")
        for answer in self.answerList:
            if self.valid(answer):
                try:
                    self.valueList.append(trueType.castRawAnswer(answer["complete_id"],
                                                                 answer["value"]))
                except:
                    pass
        self.widget = survey_analysis_type[trueType](question_id, self.answerList)

    def drawChart(self, output="xml",
                  data=None, label=None, xLabel=None, yLabel=None):
        return self.widget.drawChart(output, data, label, xLabel, yLabel)

# END =========================================================================
