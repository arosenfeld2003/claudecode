What is a Ralph loop?
Ralph loops (named after Ralph Wiggum) were introduced by Geoffrey Huntley (the Australian legend).
The concept is super simple (why it’s named after the simpsons character):
You run your AI agent in an extremely simple bash loop. When it finishes a task, it starts with clean context.
What does it fix?
Instead of having context rot over a session, you are implementing the idea of having very simple sessions and constant restarting.
The agent finishes a task, immediately starts another agent (instead of having the same agent running over a long session).
The context is new, but the project/tasks are shared.
The way the agent is able to do this is by using file management.
The plugin problem
Here’s where everything is going wrong.
If you’ve installed a “Ralph Wiggum” plugin for Claude Code, I have news.
You aren’t properly doing Ralph loops.
Huntley himself has said the Anthropic plugin “is not it”. The reason is really simple, where the loop runs is important.
A proper Ralph loop runs outside of your AI agent. Able to control something like Claude Code, kill the session and restart it whenever it needs.
Most plugins do the opposite, the loop runs inside Claude Code. Allowing Claude Code to control the loop.

Correct Ralph loop
[ Simple bash loop ]
  -> [ Claude Code instance ]
Plugin loop
[ Claude Code instance ]
  -> [ Ralph loop plugin ]
In the first setup, the bash loop decides when to start, stop, and restart Claude Code.
In the second, Claude Code is in charge. All the loop does is basically prevent the completion. You still have the same context, compression, and essentially context rot.
You’re not solving context rot. You’re just making Claude work longer and use more tokens (actually providing more rot).

Array problem
Huntley explains it very clearly like this:
“context windows are arrays”
What happens with the array:
* 		Every message you send is added.
* 		Every response is added.
* 		Eventually the array is too long.
* 		Compression/compaction starts.
Compression/compaction loses data. A summary of past conversation history, losing context. Typically at the beginning (where key instructions live) context is lost.


Huntley likes to call this:
“deterministically malicking the array”
This basically means, the less you use the array, the less the context window needs to compress, the better outcome you get.

Using a screwdriver, before a power drill
A common saying in building is:
“Start by hand, finish with the gun”
This saying basically means, start with control and safety before you focus on speed.
Huntley constantly repeats this:
“Learn how to use a screwdriver first. Really important. Don’t jump straight to the power tools.”

Before you run a Ralph loop overnight, you should:
* 		Create specs (markdown) through a conversation (not manually).
* 		Run it yourself manually (watch what it does).
* 		Make required adjustments to your prompt.
* 		Now watch and run the Ralph loop
Most people skip straight to the power drill. Install a plugin, write an incorrect prompt, get a bad output, and spend a lot of tokens in the process.

How Geoffrey Huntley does it

Step 1 — He creates specs through AI conversation.
He doesn’t manually write these, instead, he generates them and uses conversation with Claude, then reviews and edits them.
The conversation builds the context, he likes to call it “moulding the clay on the pottery wheel”.

Step 2 — Set up a PIN.
A pin is a Markdown file, it includes lookup tables that link to specific features with descriptions.
The reason he does this is to allow the agent to be able to find context a lot easier instead of hallucinating and inventing things.
This is quite similar to the plan mode in Cursor.

Step 3 — Create a prompt.
His prompt will surprise you:
Study specs/readme.md
Study specs/implementation-plan.md
Pick the most important thing to do
He doesn’t tell it which task to do. The agent decides what’s most important.
Telling the agent to pick the most important thing to do is extremely useful, as otherwise it would likely do it sequentially, which creates worse results over time.

Step 4 — Adding a completion loop.
When tests pass, commit and push
Update the implementation plan when the task is done
This step, in my opinion, is the single most important.
Make sure to add the best verification possible. This follows what the creator of Claude Code mentioned, which I covered in this post.

Step 5 — Run it while watching.
while true; do
  cat prompt.md | claude --dangerously-skip-permissions
done
He runs it, watches. If something’s wrong, he cancels it. Then adjusts the prompt.

One mission per loop
Keeping this simple and correct is crucial.
Each loop should have only one goal/objective/task.
Not something like:
* 		“Build this feature e2e”.
* 		“Implement all of feature X and Y”.
It should be one thing.
The agent will complete that one thing, commit the changes, update the plan, then kill the process.
The next loop will then pick up the next most important thing to do.
Keep each loop focused and simple, using less of the context window. Allowing for less rot and better outcomes.

The cost
Huntley claims Ralph Loops cost about $10 an hour using Sonnet.
In that hour, you’re outputting a lot of work.
If that number seems high, then you are likely not using the loop correctly. You need to spend more time prepping for the loop instead of just running it.
Done correctly, it can ship massive features.

What really matters
Personally, after experimenting, this is what I’ve learned:
The technique does work. Only when it’s set up correctly (the plugins don’t do it correctly).
Markdown files matter more than the loop itself. Your specifications are key, if done badly, you may as well not run the loop at all.
Don’t just let it run autonomously. I’m going to be honest, this is what I did when I first tried it. The amount of tokens it used and the bad output it gave made me want to understand how it worked in the first place.
One task per loop. It is tempting to try and run multiple tasks, this is the exact same for AI coding without a Ralph loop. Trying to tackle too many tasks simply gives bad outcomes.
