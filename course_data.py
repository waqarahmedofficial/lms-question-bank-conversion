# -*- coding: utf-8 -*-
"""
Source data for the sample course "Workplace Communication Essentials".
Original content written for this proof sample. Consumed by gen_mbz.py.
Question tuple formats (kept compact on purpose):
  mc_single / mc_multi : (name, text, [(answer, fraction, feedback), ...], general_feedback)
  truefalse            : (name, text, correct_is_true_bool, feedback_true, feedback_false, general_feedback)
  shortanswer          : (name, text, [(answer, fraction), ...], general_feedback)
  matching             : (name, text, [(subquestion, subanswer), ...], general_feedback)
  numerical            : (name, text, value, tolerance, general_feedback)
  essay                : (name, text, grader_info, general_feedback)
  calculated           : (name, text_with_{wildcards}, formula, [(wildcard, min, max, decimals)], general_feedback)
Some questions carry "img": filename to embed an image in the question text.
"""

COURSE = {
    "fullname": "Workplace Communication Essentials",
    "shortname": "WCE-101",
    "summary": ("A short practical course on clear workplace writing, feedback and meetings. "
                "Built as a conversion proof sample: it deliberately contains pages, files, "
                "an assignment with a rubric, completion prerequisites, a SCORM package and a "
                "63-question bank so the conversion can be tested against real counts."),
}

SECTIONS = [
    {"name": "Getting Started: Communication Basics",
     "summary": "Why communication succeeds or fails, and how this course works."},
    {"name": "Writing Clearly at Work",
     "summary": "Plain language, structure and tone in everyday workplace writing."},
    {"name": "Meetings, Feedback and Difficult Conversations",
     "summary": "Running useful meetings and giving feedback people can act on."},
    {"name": "Final Review and Workplace Scenarios",
     "summary": "Scenario practice and the final quiz."},
]

# Activities: dicts consumed by gen_mbz.py. "section" is 1-based.
ACTIVITIES = [
    {"type": "page", "section": 1, "name": "Welcome and How This Course Works",
     "completion": 1,  # tracked, manual
     "content": ("<p>Welcome to <strong>Workplace Communication Essentials</strong>. "
                 "Most workplace problems are communication problems in disguise: an unclear email, "
                 "a meeting with no decision, feedback that arrives too late to use.</p>"
                 "<p><img src=\"@@PLUGINFILE@@/banner.png\" alt=\"Course banner\" width=\"900\"></p>"
                 "<p>Work through the four sections in order. Each section ends with a short check "
                 "so you can see what has actually landed.</p>")},
    {"type": "label", "section": 1, "name": "Start here label",
     "content": "<p><em>Start here: read the welcome page, then download the course handbook.</em></p>"},
    {"type": "resource", "section": 1, "name": "Course Handbook (PDF)",
     "file": "handbook.pdf", "completion": 1,
     "intro": "The full course handbook as a single PDF document."},
    {"type": "page", "section": 1, "name": "The Sender-Message-Feedback Loop",
     "requires": "Welcome and How This Course Works",  # completion prerequisite
     "content": ("<p>Every message travels a loop: a <strong>sender</strong> encodes an idea, the "
                 "<strong>message</strong> crosses a channel, a <strong>receiver</strong> decodes it, "
                 "and <strong>feedback</strong> tells the sender whether it landed as intended.</p>"
                 "<p><img src=\"@@PLUGINFILE@@/loop-diagram.png\" alt=\"Sender message receiver feedback loop\" width=\"720\"></p>"
                 "<p>Most breakdowns happen at encoding (the idea was never made explicit) or at "
                 "feedback (nobody checked understanding). This course trains both ends of the loop.</p>")},
    {"type": "page", "section": 2, "name": "Plain Language at Work",
     "content": ("<p>Plain language is not dumbed-down language. It is writing that a busy reader "
                 "can act on after one reading: short sentences, common words, the action stated "
                 "before the background.</p><p>Compare: <em>“It has been decided that the submission "
                 "of reports will henceforth be effectuated on a weekly basis”</em> with "
                 "<em>“From Monday, send your report every Friday.”</em> Same decision — the second "
                 "version can be obeyed immediately.</p>")},
    {"type": "assign", "section": 2, "name": "Rewrite a Workplace Email",
     "intro": ("Take the badly written email in the course handbook (page 4) and rewrite it using the "
               "plain-language rules from this section. Maximum 150 words. Submit your rewrite as text."),
     "rubric": [
         ("Clarity of the main point", ["Main point is missing or buried.", "Main point appears but late in the message.", "Main point is stated in the first two lines."]),
         ("Plain language", ["Long sentences and jargon throughout.", "Some sentences simplified; jargon remains.", "Short sentences, common words, no unexplained jargon."]),
         ("Action and deadline", ["No clear action or deadline.", "Action stated but deadline vague.", "Exactly one clear action with a specific deadline."]),
         ("Tone", ["Tone is abrupt or overly formal.", "Tone is acceptable but inconsistent.", "Tone is polite, direct and consistent throughout."]),
     ]},
    {"type": "resource", "section": 2, "name": "Plain Language Style Checklist",
     "file": "checklist.txt", "completion": 1,
     "intro": "A one-page checklist to run through before sending any workplace message."},
    {"type": "quiz", "section": 2, "name": "Quiz 1: Writing Clearly",
     "intro": "Ten questions on plain language and structure.", "question_names": "QUIZ1"},
    {"type": "page", "section": 3, "name": "Giving Feedback That Lands",
     "requires": "Quiz 1: Writing Clearly",  # completion prerequisite
     "content": ("<p>Useful feedback is <strong>specific</strong>, <strong>soon</strong> and about "
                 "<strong>behaviour</strong>, not personality. “The report's summary repeated the "
                 "introduction, so the client missed the deadline change” can be acted on. "
                 "“You are careless” cannot.</p><p>Describe what you observed, the effect it had, "
                 "and what you need next time — in that order.</p>")},
    {"type": "resource", "section": 3, "name": "Interactive Scenario: The Missed Deadline (SCORM 1.2)",
     "file": "scorm-missed-deadline.zip", "completion": 1,
     "intro": "A small interactive SCORM 1.2 scenario package about handling a missed deadline conversation."},
    {"type": "quiz", "section": 3, "name": "Quiz 2: Meetings and Feedback",
     "intro": "Ten questions on meetings and feedback.", "question_names": "QUIZ2"},
    {"type": "quiz", "section": 4, "name": "Final Quiz: Workplace Scenarios",
     "intro": "Scenario questions drawn from the whole question bank.", "question_names": "QUIZ3"},
    {"type": "label", "section": 4, "name": "Completion note label",
     "content": "<p><em>When every quiz shows complete, you have finished the course. Save your handbook — the checklists are the part people actually reuse.</em></p>"},
]

MC_SINGLE = [
    ("MC01 first step unclear message", "A colleague replies “This doesn't work” to your project update, with no detail. What is the best first step?",
     [("Ask a specific question about which part fails and what they expected", 1.0, "Correct — a specific question restarts the feedback loop."),
      ("Rewrite the whole update and resend it", 0.0, "Rewriting everything guesses at the problem and wastes effort."),
      ("Escalate to their manager immediately", 0.0, "Escalation is a last step, not a first one."),
      ("Wait a week and hope it resolves", 0.0, "Waiting lets a small misunderstanding grow.")],
     "When a message is unclear, ask one specific question rather than guessing."),
    ("MC02 meeting purpose", "What is the most important thing to state at the start of a meeting?",
     [("The decision or outcome the meeting must produce", 1.0, "Correct — a stated outcome keeps discussion on track."),
      ("The full history of the project", 0.0, "History matters, but only after the purpose is clear."),
      ("Who is to blame for delays", 0.0, "Blame shuts down contribution."),
      ("The seating arrangement", 0.0, "Logistics never outrank purpose.")],
     "Meetings without a stated outcome drift."),
    ("MC03 email subject line", "Which subject line is most effective for an action email?",
     [("Action needed by Friday: approve the rota", 1.0, "Correct — action, topic and deadline in one line."),
      ("Hello", 0.0, "A greeting is not a subject."),
      ("Important!!!", 0.0, "Urgency without a topic forces the reader to open and guess."),
      ("Re: Re: Re: update", 0.0, "Thread debris tells the reader nothing.")],
     "A good subject line carries the action, the topic and the deadline."),
    ("MC04 active listening", "Which behaviour best shows active listening in a conversation?",
     [("Summarising what the speaker said and checking you understood", 1.0, "Correct — summarising proves and tests understanding."),
      ("Preparing your reply while they talk", 0.0, "Preparing a reply means you stopped listening."),
      ("Nodding continuously without speaking", 0.0, "Nodding alone does not verify understanding."),
      ("Finishing the speaker's sentences", 0.0, "Finishing sentences hijacks the speaker's meaning.")],
     "Summarise and check — that is listening made visible."),
    ("MC05 channel choice", "A sensitive performance issue needs discussing with a team member today. Which channel fits best?",
     [("A private conversation, face to face or by video call", 1.0, "Correct — sensitive topics need a private, two-way channel."),
      ("A group email to the whole team", 0.0, "Group email exposes a private matter."),
      ("A message in the team chat channel", 0.0, "Chat is too public and too easy to misread."),
      ("A note left on their desk", 0.0, "A note gives no chance to respond or clarify.")],
     "Match the channel to the sensitivity of the message."),
    ("MC06 jargon", "A report for new starters contains the phrase “synergise cross-functional deliverables”. What is the plain-language problem?",
     [("It uses jargon the reader cannot act on", 1.0, "Correct — if the reader cannot act, the words failed."),
      ("It is too short", 0.0, "Length is not the issue here."),
      ("It needs more capital letters", 0.0, "Capitalisation does not fix meaning."),
      ("It should be in a table", 0.0, "Format cannot rescue empty wording.")],
     "Jargon that cannot be acted on is noise, however impressive it sounds."),
    ("MC07 feedback timing", "When is feedback most useful?",
     [("Soon after the event, while details are fresh", 1.0, "Correct — fresh detail makes feedback specific."),
      ("At the annual review, saved up", 0.0, "Saved-up feedback arrives too late to change anything."),
      ("Only when the person asks for it", 0.0, "Waiting to be asked means problems repeat."),
      ("In front of the whole team", 0.0, "Public feedback humiliates and rarely helps.")],
     "Specific and soon beats stored and annual."),
    ("MC08 chart channel question", "Look at the chart in this question. Which channel did staff choose most often for quick updates?",
     [("Team chat", 1.0, "Correct — the chart shows team chat as the tallest bar."),
      ("Email", 0.0, "Email is second in the chart."),
      ("Notice board", 0.0, "The notice board is the least chosen."),
      ("Phone call", 0.0, "Phone calls sit in the middle of the chart.")],
     "Read the tallest bar first — it is the headline of any chart.", "chart.png"),
    ("MC09 chart least chosen", "Using the same chart, which channel was chosen least often?",
     [("Notice board", 1.0, "Correct — the notice board has the shortest bar."),
      ("Team chat", 0.0, "Team chat was chosen most, not least."),
      ("Email", 0.0, "Email was the second most chosen."),
      ("Phone call", 0.0, "Phone calls were mid-ranked.")],
     "The shortest bar is the least chosen option.", "chart.png"),
    ("MC10 agenda item", "Which of these is a well-formed agenda item?",
     [("Decide: choose the supplier for the office move (15 minutes)", 1.0, "Correct — a decision verb, a topic and a time box."),
      ("Office move", 0.0, "A topic alone does not say what must happen."),
      ("Miscellaneous", 0.0, "Miscellaneous invites drift."),
      ("Updates", 0.0, "Updates with no decision usually belong in an email.")],
     "Agenda items need a verb, a topic and a time."),
    ("MC11 tone in writing", "A request email ends with “Send this TODAY.” in capitals. What is the likely effect on the reader?",
     [("It reads as shouting and creates resistance", 1.0, "Correct — capitals read as shouting in writing."),
      ("It guarantees a faster reply", 0.0, "Pressure usually slows cooperation."),
      ("It makes the deadline legally binding", 0.0, "Capitals carry no legal force."),
      ("It has no effect at all", 0.0, "Tone always has an effect.")],
     "In writing, capitals and exclamation marks set the volume."),
    ("MC12 cc usage", "When is it appropriate to copy a manager into an email thread?",
     [("When the manager genuinely needs the information or a decision is stuck", 1.0, "Correct — copying is for information or unblocking, not pressure."),
      ("To pressure a colleague into replying faster", 0.0, "Copying as pressure damages trust."),
      ("On every email you send", 0.0, "Copying everyone trains people to ignore you."),
      ("Only after an argument starts", 0.0, "Late copying looks like escalation theatre.")],
     "Copy people who need the content, not people you want as leverage."),
    ("MC13 minutes", "What should meeting minutes record above all else?",
     [("Decisions made and who owns each action", 1.0, "Correct — decisions and owners are the working record."),
      ("Everything everyone said, word for word", 0.0, "Transcripts bury the decisions."),
      ("Only the apologies", 0.0, "Apologies are the least useful part to record."),
      ("The chair's opinions", 0.0, "Minutes record the group's decisions, not one person's views.")],
     "Minutes exist so absent people can see decisions and owners."),
    ("MC14 difficult news", "You must tell a client a deadline will slip by two days. What is the best structure?",
     [("State the slip early, give the reason briefly, offer the new date and a remedy", 1.0, "Correct — early, brief, and with a remedy."),
      ("Hide the slip in the middle of a long update", 0.0, "Burying bad news destroys trust when found."),
      ("Blame a supplier in detail", 0.0, "Blame does not restore the client's plan."),
      ("Wait until the original deadline passes", 0.0, "Late surprises are the worst option.")],
     "Bad news: early, brief, with a remedy."),
    ("MC15 questions in meetings", "A meeting keeps circling the same point. What question helps most?",
     [("“What exactly are we deciding in the next ten minutes?”", 1.0, "Correct — naming the decision breaks the circle."),
      ("“Who disagrees with me?”", 0.0, "That question polarises the room."),
      ("“Can we talk longer?”", 0.0, "More time rarely fixes an unnamed decision."),
      ("“Whose fault is this?”", 0.0, "Fault-finding restarts the circle.")],
     "Name the decision to break a circular discussion."),
    ("MC16 written handover", "A good written handover note must always include…",
     [("Current status, open issues and the next action with its owner", 1.0, "Correct — status, open issues, next action and owner."),
      ("Your full employment history", 0.0, "Irrelevant to the work being handed over."),
      ("Every email ever sent about the task", 0.0, "Volume buries the current state."),
      ("Only the good news", 0.0, "Hiding open issues sets up the next person to fail.")],
     "A handover that hides problems is a trap for the next person."),
    ("MC17 loop diagram", "In the communication loop diagram in this question, what travels from the receiver back to the sender?",
     [("Feedback", 1.0, "Correct — feedback closes the loop."),
      ("The channel", 0.0, "The channel carries the message, it is not what returns."),
      ("Noise", 0.0, "Noise interferes; it is not the return path."),
      ("The agenda", 0.0, "Agendas belong to meetings, not the basic loop.")],
     "Feedback is the return path that closes the loop.", "loop-diagram.png"),
]

MC_MULTI = [
    ("MM01 clear email parts", "Which THREE elements make an action email clear? (Choose all that apply.)",
     [("The action stated in the first lines", 1.0, "Yes — action first."),
      ("A specific deadline", 1.0, "Yes — deadlines make actions schedulable."),
      ("One topic per email", 1.0, "Yes — one topic keeps replies clean."),
      ("Several unrelated requests bundled together", 0.0, "Bundling unrelated requests buries each one."),
      ("A long background history before the request", 0.0, "Background first makes readers work for the point.")],
     "Action, deadline, one topic — the three legs of a clear email."),
    ("MM02 feedback qualities", "Which of these make feedback more likely to be acted on? (Choose all that apply.)",
     [("It describes observable behaviour", 1.0, "Yes — behaviour can change; personality labels cannot."),
      ("It is given soon after the event", 1.0, "Yes — fresh feedback is specific feedback."),
      ("It states the effect of the behaviour", 1.0, "Yes — effects create the reason to change."),
      ("It compares the person to a colleague", 0.0, "Comparisons create resentment, not change."),
      ("It is delivered by surprise in a group setting", 0.0, "Ambush feedback triggers defence.")],
     "Behaviour, effect, soon — feedback that lands."),
    ("MM03 meeting roles", "Which roles help a meeting run well? (Choose all that apply.)",
     [("A chair who keeps the group to the agenda", 1.0, "Yes — the chair protects the purpose."),
      ("A note-taker recording decisions and owners", 1.0, "Yes — decisions unrecorded are decisions unmade."),
      ("A timekeeper who flags overrun items", 1.0, "Yes — time boxes only work if someone guards them."),
      ("A person who re-opens settled decisions", 0.0, "Re-opening settled items burns the group's time."),
      ("Someone answering email throughout", 0.0, "Divided attention drags every discussion.")],
     "Chair, note-taker, timekeeper — small roles, big effect."),
    ("MM04 plain language edits", "Which edits improve plain language? (Choose all that apply.)",
     [("Replacing “utilise” with “use”", 1.0, "Yes — the shorter word means the same."),
      ("Splitting a 60-word sentence into three", 1.0, "Yes — one idea per sentence."),
      ("Moving the action to the start of the sentence", 1.0, "Yes — action first reads fastest."),
      ("Adding more formal phrases to sound senior", 0.0, "Formality is not clarity."),
      ("Replacing numbers with “some” and “several”", 0.0, "Vague quantities hide the facts.")],
     "Shorter words, shorter sentences, action first."),
    ("MM05 remote communication risks", "Which are real risks of written-only communication? (Choose all that apply.)",
     [("Tone being misread without voice or expression", 1.0, "Yes — tone is the first casualty in text."),
      ("Messages being skimmed and partly missed", 1.0, "Yes — skimming is the default reading mode."),
      ("Threads splitting across several channels", 1.0, "Yes — split threads lose context."),
      ("Words changing meaning as they travel", 0.0, "Written words are stable; interpretations vary, the text does not."),
      ("Handwriting being hard to read", 0.0, "Typed text has no handwriting problem.")],
     "Tone, skimming and split threads — design your writing against all three."),
    ("MM06 preparation for a call", "Before an important call, which preparations help? (Choose all that apply.)",
     [("Writing down the one outcome you need", 1.0, "Yes — one outcome focuses the whole call."),
      ("Listing the facts the other person will ask for", 1.0, "Yes — anticipated facts prevent follow-up calls."),
      ("Deciding what you can agree to on the spot", 1.0, "Yes — knowing your mandate speeds agreement."),
      ("Planning to improvise every answer", 0.0, "Improvisation is not a preparation strategy."),
      ("Booking a room with no door", 0.0, "Privacy matters for important calls.")],
     "Outcome, facts, mandate — prepare all three."),
    ("MM07 summarising skills", "A good summary of a long document… (Choose all that apply.)",
     [("Keeps every decision and deadline", 1.0, "Yes — decisions and deadlines are non-negotiable content."),
      ("Drops repetition and background colour", 1.0, "Yes — colour is what summaries exist to remove."),
      ("Keeps the original order of importance", 1.0, "Yes — reordering by importance is the summariser's job."),
      ("Adds the summariser's opinions as facts", 0.0, "Opinions must never smuggle in as facts."),
      ("Copies the longest paragraphs in full", 0.0, "Copying defeats the purpose of a summary.")],
     "Keep decisions, drop colour, never smuggle opinions."),
    ("MM08 closing a conversation", "Which phrases close a conversation clearly? (Choose all that apply.)",
     [("“So we agree: you will send the draft by Thursday.”", 1.0, "Yes — agreement, owner and deadline in one line."),
      ("“Let me summarise what we decided…”", 1.0, "Yes — a closing summary catches misunderstandings."),
      ("“I will confirm this in an email today.”", 1.0, "Yes — a written follow-up locks the agreement."),
      ("“Well, whatever happens, happens.”", 0.0, "That closes nothing and owns nothing."),
      ("“You know what I mean.”", 0.0, "Assumed understanding is how errors are born.")],
     "Close with agreement, summary and a written follow-up."),
]

TRUEFALSE = [
    ("TF01 plain language meaning", "Plain language means removing all technical terms, even when the reader needs them.", False,
     "Correct — plain language explains necessary terms; it does not ban them.", "Not quite — necessary terms stay, but they get explained.", "Plain language keeps needed terms and explains them."),
    ("TF02 subject line optional", "An email to a close colleague does not need a subject line.", False,
     "Correct — subject lines help every reader, close colleagues included.", "Not quite — subject lines still help searching and scanning.", "Every email benefits from a subject line."),
    ("TF03 feedback personality", "Feedback about a person's personality is easier to act on than feedback about behaviour.", False,
     "Correct — behaviour can change; personality labels only wound.", "Not quite — behaviour is the actionable level.", "Always aim feedback at observable behaviour."),
    ("TF04 silence agreement", "In a meeting, silence after a proposal usually means everyone agrees.", False,
     "Correct — silence more often means confusion or reluctance.", "Not quite — silence must be tested, not assumed.", "Test silence with a direct question."),
    ("TF05 one topic per email", "Keeping one topic per email makes threads easier to follow and search later.", True,
     "Correct — single-topic threads stay findable.", "Not quite — one topic per email is a proven thread-saver.", "One topic per email keeps the record clean."),
    ("TF06 capitals emphasis", "Writing a whole sentence in capital letters is a good way to add emphasis in email.", False,
     "Correct — capitals read as shouting.", "Not quite — capitals read as shouting, not emphasis.", "Use words, not volume, for emphasis."),
    ("TF07 minutes optional", "If everyone attended the meeting, minutes are unnecessary.", False,
     "Correct — minutes serve memory and absent stakeholders, not attendance.", "Not quite — decisions fade from memory within days.", "Minutes protect decisions after memory fades."),
    ("TF08 question restate", "Restating a question in your own words before answering can prevent wasted work.", True,
     "Correct — restating catches misread questions early.", "Not quite — restating is a cheap error-catcher.", "Restate first when a request is ambiguous."),
    ("TF09 more channels better", "Sending the same message on email, chat and text guarantees it will be acted on.", False,
     "Correct — duplicated messages create confusion about where to reply.", "Not quite — one channel, clearly, beats three channels noisily.", "Pick one channel and write clearly."),
    ("TF10 apology opening", "Opening difficult news with a long apology makes the news easier to accept.", False,
     "Correct — long apologies delay the fact and sound evasive.", "Not quite — state the fact first; apologise briefly after.", "Fact first, brief apology, then the remedy."),
]

SHORTANSWER = [
    ("SA01 element missing", "In the sender-message-feedback loop, which element tells the sender whether the message was understood?",
     [("feedback", 1.0), ("Feedback", 1.0)], "The missing element is feedback."),
    ("SA02 decision record", "What single word names the written record of decisions and action owners from a meeting?",
     [("minutes", 1.0), ("Minutes", 1.0), ("meeting minutes", 0.5)], "The record is the minutes."),
    ("SA03 subject content", "In an action email, the subject line should end with the action's _____. (One word: the date by which it must be done.)",
     [("deadline", 1.0), ("Deadline", 1.0)], "The deadline belongs in the subject line."),
    ("SA04 behaviour word", "Feedback should describe observable _____ rather than personality. (One word.)",
     [("behaviour", 1.0), ("behavior", 1.0), ("Behaviour", 1.0)], "Describe behaviour, not personality."),
    ("SA05 plain word", "Give the plain-language replacement for the word “utilise”.",
     [("use", 1.0), ("Use", 1.0)], "“Use” replaces “utilise”."),
    ("SA06 agenda verb", "A good agenda item starts with a verb that names a _____. (One word: the thing the group must settle.)",
     [("decision", 1.0), ("Decision", 1.0)], "Agenda items name a decision."),
    ("SA07 listener action", "What is the name of the listening technique where you repeat the speaker's point in your own words to check it? (One word, begins with S.)",
     [("summarising", 1.0), ("summarizing", 1.0), ("Summarising", 1.0)], "The technique is summarising."),
    ("SA08 handover section", "In a handover note, after current status, the next section should list open _____. (One word.)",
     [("issues", 1.0), ("Issues", 1.0), ("problems", 0.5)], "Open issues come right after status."),
]

MATCHING = [
    ("MA01 channel to job", "Match each message to the most suitable channel.",
     [("Announcing a building closure to all staff", "Email to all staff"),
      ("Asking a colleague one quick question", "Team chat message"),
      ("Discussing a team member's performance", "Private conversation"),
      ("Publishing the final approved policy", "Intranet page")],
     "Channel follows audience and sensitivity."),
    ("MA02 document to purpose", "Match each document to its main purpose.",
     [("Agenda", "State what a meeting must decide"),
      ("Minutes", "Record decisions and owners"),
      ("Handover note", "Transfer work safely to the next person"),
      ("Checklist", "Prevent steps being missed")],
     "Each document exists to do one job well."),
    ("MA03 phrase to problem", "Match each weak phrase to its problem.",
     [("“As soon as possible”", "No real deadline"),
      ("“Someone should check this”", "No named owner"),
      ("“Let's touch base”", "No clear purpose"),
      ("“Per my last email”", "Blaming tone")],
     "Vague words hide missing decisions."),
    ("MA04 feedback sentence parts", "Match each feedback part to its function.",
     [("“I noticed the summary repeated the introduction”", "Observation"),
      ("“So the client missed the date change”", "Effect"),
      ("“Please put changes in bold next time”", "Request"),
      ("“Thanks for turning it around quickly”", "Appreciation")],
     "Observation, effect, request — in that order."),
    ("MA05 tone words", "Match each closing line to the tone it creates.",
     [("“Send it today.”", "Direct"),
      ("“Whenever you get a chance, no rush at all.”", "Too vague"),
      ("“I need this NOW!!!”", "Aggressive"),
      ("“Could you send it by 3 pm? Thanks.”", "Polite and clear")],
     "Tone is a choice, not an accident."),
    ("MA06 loop parts", "Match each part of the communication loop to its role.",
     [("Sender", "Encodes the idea"),
      ("Channel", "Carries the message"),
      ("Receiver", "Decodes the message"),
      ("Feedback", "Confirms understanding")],
     "Every loop part has exactly one job."),
]

NUMERICAL = [
    ("NU01 response time", "A team promises to reply to client emails within 4 business hours. A message arrives at 9:00 and is answered at 12:30 the same day. How many hours did the reply take?",
     3.5, 0.1, "9:00 to 12:30 is 3.5 hours — inside the promise."),
    ("NU02 word cut", "An email draft is 240 words. The plain-language target is to cut it by a quarter. How many words should the final email be?",
     180.0, 1.0, "A quarter of 240 is 60; 240 − 60 = 180 words."),
    ("NU03 meeting cost", "Six people attend a meeting that runs 30 minutes longer than planned. How many person-hours were lost to the overrun?",
     3.0, 0.1, "6 people × 0.5 hours = 3 person-hours."),
    ("NU04 reading time", "A report takes an average reader 250 words per minute. The report is 2,000 words. How many minutes does it take to read?",
     8.0, 0.5, "2,000 ÷ 250 = 8 minutes."),
    ("NU05 reply rate", "You send 40 update emails and 28 are opened. What percentage were opened?",
     70.0, 1.0, "28 ÷ 40 = 0.7, so 70%."),
    ("NU06 action items", "Minutes list 12 action items. By Friday, 9 are complete. How many remain open?",
     3.0, 0.0, "12 − 9 = 3 open items."),
]

ESSAY = [
    ("ES01 rewrite announcement", "Rewrite this announcement so a new starter could act on it after one reading: “Staff are hereby notified that the utilisation of the meeting rooms on floor three will be subject to a booking requirement henceforth.” (60–100 words.)",
     "Grader info: credit a clear statement of the rule, who it applies to, from when, and how to book.", "A strong answer states the rule, the start date and the booking method."),
    ("ES02 feedback plan", "A colleague's last two reports reached the client with errors. Write the opening three sentences of the feedback conversation you would have with them.",
     "Grader info: sentences should open with observation, then effect, then a request — no personality labels.", "Open with what you observed, not what you concluded about the person."),
    ("ES03 meeting rescue", "A weekly meeting has produced no decision in three weeks. Describe, in order, the three changes you would make to the next meeting and why each helps.",
     "Grader info: look for a stated outcome, an agenda of decisions, and recorded owners/deadlines.", "Decisions fail when outcome, agenda and ownership are all missing."),
    ("ES04 client delay email", "Write a short email to a client explaining that their document will arrive two days late, including the reason and what you will do to prevent a repeat.",
     "Grader info: the slip must appear early, the reason must be brief, and a prevention step must be named.", "Early, brief, with a remedy and a prevention."),
    ("ES05 handover note", "You are going on leave for two weeks. Write a handover note for your most important task: status, open issues, next action and owner.",
     "Grader info: all four elements must be present and the next action must have a named owner and date.", "A handover is judged by what the next person can do without asking questions."),
]

CALCULATED = [
    ("CA01 reply window", "A support team promises a first reply within {h} business hours. A ticket arrives at {s}:00 and is answered the same day at {e}:00. How many hours remain inside the promised window?",
     "{e}-{s} hours used; window remaining = {h}-({e}-{s})",
     [("h", 2, 8, 0), ("s", 8, 11, 0), ("e", 12, 16, 0)],
     "Subtract the used hours from the promised window."),
    ("CA02 words per page", "A style guide allows {w} words per page. A document has {p} pages at exactly the limit. How many words does the document contain?",
     "{w}*{p}",
     [("w", 250, 500, 0), ("p", 2, 12, 0)],
     "Multiply words per page by the number of pages."),
    ("CA03 meeting people hours", "A meeting has {n} attendees and overruns by {m} minutes. How many person-hours does the overrun cost, to one decimal place?",
     "{n}*{m}/60",
     [("n", 3, 10, 0), ("m", 10, 45, 0)],
     "Person-hours = people × minutes ÷ 60."),
]

QUIZ_MEMBERSHIP = {
    # Which named questions each quiz references (by name). Totals are informational;
    # the bank itself holds all 63 questions and every quiz draws from it.
    "QUIZ1": ["MC03 email subject line", "MC06 jargon", "MC11 tone in writing", "MM01 clear email parts",
              "MM04 plain language edits", "TF01 plain language meaning", "TF02 subject line optional",
              "TF06 capitals emphasis", "SA03 subject content", "SA05 plain word"],
    "QUIZ2": ["MC02 meeting purpose", "MC07 feedback timing", "MC10 agenda item", "MC13 minutes",
              "MM02 feedback qualities", "MM03 meeting roles", "TF03 feedback personality",
              "TF04 silence agreement", "SA02 decision record", "SA04 behaviour word"],
    "QUIZ3": ["MC01 first step unclear message", "MC05 channel choice", "MC08 chart channel question",
              "MC14 difficult news", "MC17 loop diagram", "MA03 phrase to problem", "NU03 meeting cost",
              "NU05 reply rate", "ES04 client delay email", "CA01 reply window"],
}
