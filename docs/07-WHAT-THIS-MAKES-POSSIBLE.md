# Seven things a local relationship mesh makes possible

**Why read this: the replica is not the product.** Once one person's mail, calendar,
texts and contacts resolve to a single record on your own disk, a class of things
becomes cheap that was previously impossible — not because the idea was hard, but
because the data was in four places owned by three companies.

Five of these work today. Two do not exist yet and are marked as such, because a
roadmap dressed as a feature list is how you lose a reader twice.

---

## 1. You stop walking into conversations half-blind
**Today.** `exo-mail contact show`

One person, every channel, one read: the last thread, the last text, meetings you have
shared, who usually starts the conversation, how long the relationship has run, and
every address and phone number that turns out to be the same human.

The thing this kills is subtle. You do not merely *find out* it has been six months —
you find out it has **not**, because they texted on Tuesday and only your inbox forgot.
Single-channel tools cannot tell you that, and they fail confidently.

```bash
exo-mail contact show "Priya Shah"
# → last contact 3d (imessage) · channels: email+imessage+calendar · they usually start it
```

## 2. The promises you forgot you made come back to you
**Today.** `exo-mail reconnect` → `open_promises`

You said you would send the deck. You said you would make the introduction. You said you
would look at their draft. All of it is sitting in your own sent mail, and none of it is
in any task list.

The mesh reads your sent mail for commitments you made *to that specific person* and
hands them back before you talk to them again. Nothing was captured, tagged, or
remembered by you — it was already written down, in your own words, by you.

This is the feature people do not expect and then cannot give up.

## 3. Drift tells you the truth instead of what your inbox thinks
**Today.** `exo-mail contact drift --days 120`

Every CRM and every reminder app measures one channel and calls it a relationship. That
produces two failures constantly: it nags you about someone you saw yesterday, and it
says nothing about someone you have not actually spoken to in a year because a calendar
invite kept the record warm.

Cross-channel drift means a relationship is quiet only when it is quiet *everywhere*. It
also means a departure is not silence: someone whose work address went dark can stay
fully alive on their personal number, and the mesh knows the difference.

## 4. You find out which relationships will survive the job that made them
**Today.** `exo-mail bedrock`

Most professional relationships are contextual — they exist because of a company, a
project, a role. When the context ends, most of them quietly end too, and you cannot
tell in advance which ones will not.

BEDROCK computes three things from the record: seven-plus years of span, two-way in at
least one channel, still alive in the last eighteen months. The fourth — *did this
survive a change of context?* — is a human judgment, and the tool records your answer
rather than guessing it.

This matters most at exactly the moment it is hardest to think clearly: a company
winding down, a role ending, a move. The list of who to reach before the shared context
disappears is computable, and almost nobody computes it.

## 5. Your agents stop guessing about your life
**Today.** `exo-mail mcp` — nine tools over the Model Context Protocol

Every agent you build wants context. The usual answers are to paste it in by hand, or to
hand a vendor a copy of your inbox and hope the retention policy is one you would have
written.

Here the context is a file on your disk and the agent reads it through a documented tool
contract with a stable JSON envelope, explicit error codes, and a clear line between the
seven tools that read and the two that write. No key on the query path. See
[AGENTS.md](../AGENTS.md).

The consequence is that "prep me for this meeting" and "who should I reconnect with"
stop being prompts you engineer and start being queries the agent can actually answer.

## 6. Who do I know who knows them
**Not built yet.** The data is already on disk.

Every thread with more than one recipient is evidence that two people know each other.
Across a real archive that is a substantial graph, and it is sitting unused in the
replica right now — a sampled read of ordinary inbox threads finds roughly a quarter
carry two or more recipients, and repeated pairs are a genuine edge rather than noise.

What that buys you: *"I want to reach someone at Acme Robotics — who do I already know
who has been on a thread with them, how recently, and how strong is my side of that
relationship?"* A warm path, ranked, computed from your own correspondence, with nobody
else's social graph involved and nothing uploaded to find it.

Every professional network product sells you a version of this built on a graph you do
not own and cannot inspect. The honest version is derivable from your own mailbox.

## 7. Context that arrives instead of being fetched
**Not built yet.** Designed; see the roadmap note below.

Knowing you *could* run `contact show` before a meeting is not the same as it being
there. The intended shape:

- a short context entry on the calendar ten minutes before each meeting — who you are
  meeting, where the relationship stands, what you owe them — with **zero attendees**,
  shown as free, never touching the source invite, on a calendar of its own so deleting
  it is one click
- a daily briefing with a three-day horizon: the meetings coming, the people in them,
  and who is drifting

The design constraint that makes this safe rather than creepy: **nothing reaches anyone
but you.** No timer sends anything to anyone else, ever. Context is delivered to the
person who owns the data, and every outbound message still waits for a human.

---

## What ties them together

None of these are hard algorithms. They are all cheap once one person resolves to one
record locally, and all effectively impossible while the same relationship lives as four
fragments behind three APIs and a rate limit.

That is the whole argument for the replica: not that local is faster — though it is
milliseconds instead of round-trips — but that **local is the only place the join can
happen at all.**
