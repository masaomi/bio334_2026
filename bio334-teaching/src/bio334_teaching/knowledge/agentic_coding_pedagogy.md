---
name: agentic_coding_pedagogy
description: Programming education philosophy and methodology for the Agentic Coding era — skills and strategies for teaching in an age of AI-human collaboration
layer: L1
version: "2.1"
tags:
  - pedagogy
  - agentic-coding
  - education
  - philosophy
  - teaching-strategy
---

# Programming Education in the Agentic Coding Era

## Recognizing the Shift: What Has Changed

### Traditional Programming Education
- **Goal**: Write syntactically correct code
- **Assessment**: Can the student produce working code without syntax errors?
- **Implicit assumption**: Humans write code line by line

### Education in the Agentic Coding Era
- **Goal**: Understand the problem, instruct AI effectively, and verify the output
- **Assessment**: Can the student explain the meaning of a computation? Can they critically evaluate AI-generated output?
- **Assumption**: AI generates the code. Humans are responsible for the "what" and the "why"

## Four-Layer Model of Education

### Layer 1: Conceptual Understanding
> "Can you explain what is being computed?"

- Explain mathematical formulas in plain language
- Articulate why a given computation is necessary
- Judge the plausibility of results
- **Example**: "Pi (pi) is a measure of genetic diversity within a population -- the average proportion of nucleotide differences across all pairwise comparisons of sequences"

### Layer 2: Instruction Ability
> "Can you give precise instructions to AI?"

- Decompose a problem and verbalize each step
- Specify input and output requirements explicitly
- Communicate edge cases and constraints
- **Example**: "Write a Python function that reads sequences from a FASTA file, counts pairwise nucleotide differences for all pairs, normalizes by sequence length, and computes pi"

### Layer 3: Implementation Literacy
> "Can you read and verify the code?"

- Follow the logic of AI-generated code
- Identify bugs and inefficiencies
- Make minimal corrections independently
- **Example**: Understanding the meaning of nested loops and the origin of the combinatorial factor n(n-1)/2

### Layer 4: Result Verification
> "Can you interpret the results biologically?"

- Evaluate whether computed values are plausible
- Interpret results in biological context (e.g., "low pi suggests a selective sweep")
- Compare results across conditions and explain differences
- Connect numerical outputs to the biological question that motivated the analysis
- **Example**: "The halleri-derived HMA4 shows pi = 0.0008, about 11x lower than the lyrata copy. This is consistent with a selective sweep on the functionally important heavy metal transporter."

## Scaffolding Strategy

### Principle: Gradual Transfer of Autonomy

```
Phase 1: Fully Guided
  Teaching Chain: Explain concepts -> Present code skeleton -> Fill-in-the-blank exercises
  Learner: Listen to explanation -> Fill in gaps -> Run and verify

Phase 2: Partial Autonomy
  Teaching Chain: Confirm understanding -> Present the problem
  Learner: Write their own prompts to AI -> Verify results -> Ask questions about unclear points

Phase 3: Full Autonomy
  Teaching Chain: Present only the problem (e.g., A. kamchatica data analysis)
  Learner: Decompose the problem -> Collaborate with AI to solve it -> Interpret results
```

### Types of Scaffolding

1. **Conceptual scaffolding**: Providing biological context (What is pi? Why does it matter?)
2. **Structural scaffolding**: Presenting a step-by-step problem decomposition (Step 1: Read sequences -> Step 2: Pairwise comparison -> ...)
3. **Code scaffolding**: Skeleton code (function signatures and type hints)
4. **Verification scaffolding**: Providing expected output values ("If pi = 0.05 for this input, the result is correct")

## Methods for Assessing Understanding

### Explain-Back Method
Ask learners to explain concepts **in their own words**:
- "Explain nucleotide diversity to a friend who has no biology background"
- "Describe two biological scenarios in which Tajima's D would be negative"

### Predict-Before-Run Method
Ask learners to predict the result before running the code:
- "Roughly how large do you expect pi to be for this set of sequences?"
- "If you increase the population size tenfold, how would Tajima's D change?"

### Debug Challenge
Present code with intentional bugs and ask learners to find them:
- "This nucleotide diversity calculation contains one bug. Find it."
- Have learners independently verify AI-generated code

### Prompt Engineering Exercise
Practice writing effective instructions to AI:
- "Write a Python function to calculate pi" -> result is insufficient
- Refine the prompt and retry -> better result
- Reflect on what distinguishes a good prompt from a poor one

### AI Code Verification Checklist
Teach students to verify AI-generated code systematically:
1. **Read line by line**: Understand what each line does before running
2. **Check edge cases**: What happens with empty input? Single sequence? Sequences of different lengths?
3. **Test with known data**: Run on a small dataset where you know the correct answer
4. **Verify output format**: Does the output match what you asked for?
5. **Look for common AI mistakes**: BioPython when you asked for pure Python, off-by-one errors, missing the last sequence in FASTA parsing, hardcoded paths

## Principles for Adaptive Problem Design

### Branching by Level of Understanding

```
High comprehension  -> More advanced problems (e.g., comparing halleri vs. lyrata subgenomes in A. kamchatica)
Medium comprehension -> Standard exercises (e.g., basic pi calculation implementation)
Low comprehension   -> Revisit fundamentals (e.g., manual pairwise difference calculation)
```

### Designing for Learning from Failure
- Treat errors as learning opportunities
- Ask "Why did this error occur?" before providing the answer
- Allow time for independent thinking before turning to AI

## Essential Skills to Preserve in the Agentic Era

1. **Problem decomposition** -- The ability to break a large problem into manageable steps
2. **Understanding abstraction** -- The concepts of functions, modules, and pipelines
3. **Tracing data flow** -- Grasping the input -> processing -> output chain
4. **Critical verification** -- The habit of asking "Is this actually correct?"
5. **Biological interpretation** -- Understanding the biological meaning behind the numbers

## Anti-Patterns (Pedagogical Approaches to Avoid)

- Do not force memorization of syntax (AI can write it)
- Do not make writing code from scratch the ultimate goal
- Do not require memorization of error messages (AI can interpret them)
- Do not ban AI use outright (this is disconnected from professional reality)
- Do not let students run code without conceptual understanding (no different from copy-pasting AI output)

## Progress Level Definitions

The progress tracking system uses four levels per dimension:

| Level | Meaning | How reached |
|-------|---------|-------------|
| not_assessed | Topic not yet encountered | Default |
| low | Student has engaged with the topic | Asking a substantive question about the topic |
| medium | Student demonstrates understanding | Student explains the concept AND AI confirms correctness |
| high | Confirmed mastery | Successful checkpoint assessment only (never automatic) |

**Important**: "high" is never set automatically. It requires explicit demonstration through a checkpoint exercise (Explain-Back, Predict-Before-Run, Debug Challenge, Prompt Engineering Exercise, or AI Code Verification).
