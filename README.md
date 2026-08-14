# CST8917 - Serverless Applications
## Assignment 2: Compare & Contrast — Dual Implementation of an Expense Approval Workflow

**Name:** Ruaa Thamer

**Student Number:** 040819157

**Course Code:** CST8917 - Serverless Applications

**Project Title:** Compare & Contrast Dual Implementation

**Date:** 8/14/2026


---

## Introduction
This project implements an automated, enterprise-grade expense approval workflow using two distinct Azure serverless orchestration approaches: Azure Durable Functions (code-first orchestration) and Azure Logic Apps + Azure Service Bus (visual/declarative orchestration).
The goal is to demonstrate and compare how both architectures handle state management, asynchronous human-in-the-loop decisions, timeouts, event-driven messaging, and validation.

---

### Workflow & Business Rules

Both implementations adhere to the following business requirements and rules:

| Rule | Description |
| :--- | :--- |
| **Input Data** | Each expense request requires: `employee_name`, `employee_email`, `amount`, `category`, `description`, and `manager_email`. |
| **Validation** | Rejects any request missing a required field or containing an invalid category. Valid categories are: `travel`, `meals`, `supplies`, `equipment`, `software`, `other`. |
| **Auto-Approve** | Expenses under $100 are automatically approved immediately without requiring manager intervention. |
| **Manager Approval** | Expenses of $100 or more require explicit manager approval. The system halts and waits for a manager's decision (`APPROVE` or `REJECT`). |
| **Timeout Handling** | If no manager response is received within the timeout window (2 minutes for testing), the request is automatically approved and flagged with an `ESCALATED` status. |
| **Notification** | An email notification is sent to the employee with the final outcome (`APPROVED`, `REJECTED`, or `ESCALATED`) and the associated reason. |


---

## Version A — Azure Durable Functions

### 1. Architecture (How it is built)
This version uses four main pieces of code working together:
* **HTTP Starter:** Catches the incoming expense request and starts the main workflow.
* **Orchestrator:** The "manager" of the code. It controls the steps (validate, check amount, wait for manager, send email) and remembers where it left off.
* **Activities:** The "workers" that do the actual jobs, like checking if the data is correct and sending the final email.
* **Manager Webhook:** A special link created just for the manager to send their "Approve" or "Reject" decision.

### 2. Key Design Decisions
* **All in One File:** I used the Python v2 model, which let me keep all the different functions neatly organized inside a single `function_app.py` file.
* **The "Race" Condition:** To handle the manager timeout, I made the timer and the manager's decision race each other. If the manager doesn't click a button in 2 minutes, the timer wins and automatically marks the expense as "Escalated."
* **Safe Validation:** I put all the data checking (like making sure the amount is an actual number) into its own separate step. This keeps the main orchestrator safe from crashing if a user types in bad data.

### 3. Demo of it Working
1. **Send a Request:** I use the `test-durable.http` file to send a test expense report (e.g., $150 for Travel).
2. **Check Status:** The system gives back a status link. When I click it, it shows the workflow is "Running" and waiting for the manager.
3. **Manager Decision:** I send an "Approve" message to the manager webhook link.
4. **Final Result:** The workflow wakes back up, processes the approval, and prints the final "Notified: APPROVED" message in the terminal logs.
---

## Version B — Azure Logic Apps + Service Bus

### 1. Architecture (How it is built)
This version connects built-in Azure cloud tools together using a visual designer:
* **Service Bus Queue:** Acts as the "waiting room." It receives the incoming expense requests and holds them safely until the Logic App is ready.
* **Logic App:** The main visual workflow. It wakes up when a new message arrives, guides the data through each step, and makes decisions using visual condition blocks (if/else).
* **Validator Function:** A small Azure Function I built just to check if the data is correct and follow the category rules.
* **Email Connector:** A built-in Office 365 tool that sends real emails to the employee and the manager.

### 2. Key Design Decisions
* **Visual Manager Approval:** Instead of writing complex timer code, I used the built-in "Send Email with Options" action. It automatically emails the manager with "Approve" and "Reject" buttons and pauses the workflow until they click one.
* **Decoding the Message:** Service Bus hides the message data in a Base64 format. I had to use a custom formula (`base64ToString`) to translate it back into normal text so the Logic App could read it.
* **Error Handling (runAfter):** I used Logic App's `runAfter` settings to control what happens if a step fails. If the validator function finds a mistake, the workflow takes a different path to send a "Rejected" email instead of just crashing.

### 3. Demo of it Working

1. **Send a Request:** I use the Service Bus Explorer in the Azure Portal to send a test JSON expense report (e.g., $150 for Travel).
2. **Workflow Triggers:** I open the Logic App Run History and show that it successfully picked up the message and passed it to the validator function.
3. **Manager Email:** I open my inbox to show the automated email asking for approval. I click the "Approve" button right inside the email.
4. **Final Result:** I refresh the Run History to show the workflow finished successfully and show the final "Approved" email sent to the employee.
   
---

## 3. Comparison Analysis

### Development Experience

Azure Logic Apps (Version B) was quicker to get going at first — the drag-and-drop interface just made things easier. I hooked up the Service Bus and set the HTTP action right inside the Azure Portal, so I didn't have to write much boilerplate to get started. But that early speed didn't last once I had to format the data being passed between steps. For example, when sending the Service Bus message to the validator function, I found out the message was Base64-encoded by default. So I had to leave the visual menus behind and write a custom expression (`base64ToString(triggerBody()?['ContentData'])`) just to turn the data into something readable.

Azure Durable Functions (Version A), on the other hand, took more time and effort up front. Splitting the Python code into separate orchestrator, activity, and client functions wasn't something I could just wing — it took real planning to get the structure right. But once that was in place, writing the actual business logic in Python left me feeling a lot more sure it was actually working the way it was supposed to. With plain code, I could see exactly what was happening at every step, and I had direct control over the data the whole way through. Logic Apps, by comparison, tends to hide what's really going on behind all those visual screens.

### Testability

Testing locally was much easier with Azure Durable Functions (Version A). By using Azure Functions Core Tools and local storage emulators like Azurite, I could run the entire workflow right on my own computer. The `test-durable.http` file made it quick and simple to send different test data and simulate the manager's response without having to deploy anything to the cloud. Writing automated tests is also very doable for this version. Since the code is just standard Python, you can easily use testing frameworks like pytest to check each small function on its own.

On the other hand, testing the Logic Apps version (Version B) locally was almost impossible. Because it connects to a live Azure Service Bus, I had to do all my testing directly in the cloud. To see if the workflow worked, I had to manually paste test messages into the Service Bus Explorer in the Azure Portal and then check the Logic App's run history. You could technically write automated tests by creating scripts that send messages to the cloud and check the final output, but that is a lot harder and takes much more time than the simple Python unit tests in Version A.

### Error Handling

Azure Durable Functions (Version A) gives you a lot more control over failures and retries. Since it's just Python, you can wrap anything in try/except and handle specific errors however you want. It also has retry built in — you can tell an activity function to wait a certain number of seconds and try again up to a set number of times before giving up. If your app needs to handle something like a crash mid-run or a flaky network call in a very specific way, doing it in code just gives you way more room to work with.

Logic Apps takes a different approach — everything is set up through configuration instead of code. Each action comes with a retry policy already built in (by default it's exponential backoff with 4 retries) for things like timeouts. To handle failure branching, I used the `runAfter` setting, which lets an action run based on whether the previous step succeeded, failed, was skipped, or timed out. I actually ran into this myself — my validation-failure emails weren't sending because the Condition step only ran after a successful HTTP call, so I had to go in and set it to run after both Succeeded and Failed. One nice thing is that every step's inputs and outputs show up in Run History, so I could debug without digging through logs.

As for how much control I actually get: Logic Apps lets me configure retry count, interval, and type pretty easily, no code needed. But I was stuck with whatever options Logic Apps gives me — there's no way to write something like "retry 3 times but only for this error code, then fall back to a different endpoint." Durable Functions can do that because it's just code.

### Human Interaction Pattern

In Azure Durable Functions (Version A), waiting for a manager's approval required setting up a specific coding pattern. The main workflow had to go to sleep using a command called `wait_for_external_event`. To wake it up, I had to write a completely separate webhook function. When the manager makes a decision, they hit that webhook, which then sends a message back to the sleeping workflow to keep it moving. I also had to write extra code to create a timer just in case the manager never responds, forcing the system to pick a "winner" between the timer and the manager's click.

In Azure Logic Apps (Version B), handling human approval was a lot easier to set up. Logic Apps already has a built-in action for this exact situation — the "Send Email with Options" action. I just added it to the workflow, and it automatically sent an email to the manager with Approve and Reject buttons already there. Once I dropped it in, the workflow paused on its own and waited until the manager clicked one of the buttons. I didn't have to build any webhooks or write any timer logic myself to make that happen.

Because of that, this step felt way more natural to build in Logic Apps. The tool already does most of the work for you, so I didn't need to think as much about the mechanics behind it.

### Observability

Azure Logic Apps (Version B) made it much easier to monitor the workflow and figure out what went wrong. I could click into any past run and see a visual map of exactly which steps succeeded, marked with green checkmarks, and which ones failed, marked with red warning signs. I could also click on each individual box and see the exact data that went in and came out of it. This is actually how I found my "Invalid JSON payload" error so quickly — I could just see it sitting right there on the screen instead of having to dig for it.

Azure Durable Functions (Version A) was harder to monitor. Instead of a visual map, it relies on text-based logs through Azure Application Insights, so to figure out what happened during a run, I had to scroll through lines of text or write queries just to find where something failed. On top of that, because of how Durable Functions works — where the orchestrator goes to sleep and replays its code every time it wakes back up — the logs get pretty messy and repeat a lot of the same lines. It took a lot more time and effort to trace through everything compared to just glancing at the run history map in Logic Apps.

### Cost

To estimate the cost for both versions, I used the Azure Pricing Calculator along with a few basic assumptions.

**Assumptions:**

I assumed a month has 30 days.

**Version A (Durable Functions):** runs on the Azure Functions Consumption plan. I assumed each expense report triggers about 4 executions — the HTTP starter, the orchestrator waking up, the validation activity, and the notification activity.

**Version B (Logic Apps + Service Bus):** runs on the Logic Apps Consumption tier. I assumed each expense report triggers 5 actions — the trigger, formatting the data, calling the function, checking the amount, and sending an email. It also uses the Service Bus Basic tier and an Azure Function for validation.

**Cost at ~100 expenses per day (3,000 per month):**

- **Version A:** 3,000 expenses works out to roughly 12,000 function executions. Azure Functions gives you 1 million free executions a month, so since we're well under that limit, the compute cost comes out to $0.00. There might be a few cents for the background Azure Storage account, but the total is basically zero.
- **Version B:** 3,000 expenses works out to 15,000 Logic App actions. The first 4,000 actions are free. For the remaining 11,000, at $0.000025 each, that comes to around $0.27. Service Bus is extremely cheap too, at $0.05 per million messages, and the validator function stays free under the 1 million limit. So the total ends up under $1.00 a month.

**Cost at ~10,000 expenses per day (300,000 per month):**

- **Version A:** 300,000 expenses means roughly 1.2 million function executions, which goes slightly over the 1 million free grant. For the extra 200,000 executions, at $0.20 per million, that's only about $0.04. Even factoring in a few dollars for extra storage reads/writes, the total should stay under $5.00 a month.
- **Version B:** 300,000 expenses means 1.5 million Logic App actions. Subtracting the 4,000 free actions leaves 1,496,000 billable actions. At $0.000025 each, the Logic App cost jumps to $37.40. Service Bus and the validator function stay close to zero, so the total ends up around $38.00 a month.

---

## 4. Recommendation

If a team asked me to build this expense approval system for production, I would go with Version A (Durable Functions).

Logic Apps was faster to get up and running at first, but for a real, long-term project I think Durable Functions holds up better. Writing the workflow in Python gives you full control over the data and the business rules, and it's much easier to test the code locally before pushing it to the cloud. You can also write automated tests so a bad update doesn't break the whole system. On top of that, based on the cost numbers above, Durable Functions stays a lot cheaper as volume grows — keeping costs near $5 instead of $38 makes a real difference once you're dealing with thousands of requests a day.

That said, I'd pick Version B (Logic Apps) if the project required connecting to a lot of different external tools quickly, without writing much code. If the team wanted the expense system to pull data from Salesforce, update a SharePoint list, and post a message in Microsoft Teams, Logic Apps would be a much better fit — it has hundreds of pre-built connectors that can talk to these services right away. In a situation where speed of integration matters more than raw performance or cost at scale, Logic Apps is the better choice.

---

## 5. References

- [Azure Functions pricing](https://azure.microsoft.com/en-us/pricing/details/functions/)
- [Logic Apps pricing](https://azure.microsoft.com/en-us/pricing/details/logic-apps/)
- [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)


---

## 6. AI Disclosure

AI (Claude, by Anthropic) was used during this assignment in the following ways:

- **Debugging Version B (Logic Apps):** I used Claude to help find and fix a few errors while building the workflow. It helped me solve a problem with reading hidden text (Base64), fix a connection error in the HTTP step, and correct a mistake where rejected expenses weren't being separated from approved ones.
- **Report writing assistance:** I used Claude to help write and improve the sentences in this README file. I provided the details, the choices I made, and the problems I faced, and the AI helped me explain them clearly.
