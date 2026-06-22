"""
Management command: seed_blog

Creates 6 sample published blog posts for the Wild4Life website.
Idempotent — skips creation if any blog posts already exist.

Usage:
    python manage.py seed_blog
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from donations.models import BlogPost

User = get_user_model()

POSTS = [
    {
        "title": "Bringing Healthcare Closer: Our Community Outreach in Binga District",
        "excerpt": (
            "In March 2026, Wild4Life mobilised a team of nurses, community health workers, and "
            "volunteers to reach over 400 households in Binga District — many of whom had not seen "
            "a healthcare professional in over a year."
        ),
        "content": """
<p>Access to primary healthcare remains one of the most urgent challenges facing rural communities in Zimbabwe. For many families living in remote areas of Binga District, the nearest clinic is hours away — sometimes on the other side of a river that swells dangerously during the rainy season.</p>

<p>In March 2026, Wild4Life mobilised a multidisciplinary team of nurses, Village Health Workers (VHWs), and trained volunteers to bring healthcare directly to communities that are too often left behind. Over five days, the team reached more than 400 households across four wards.</p>

<h2>What the Outreach Covered</h2>
<p>The outreach was designed to address the most common and preventable health issues facing these communities. Services provided included:</p>
<ul>
  <li>Blood pressure and diabetes screening for adults over 35</li>
  <li>Maternal health checks for pregnant and post-natal mothers</li>
  <li>Child growth monitoring and immunisation updates</li>
  <li>HIV counselling and testing, with same-day results</li>
  <li>Distribution of oral rehydration salts and basic medications</li>
  <li>Health education sessions on nutrition, hygiene, and malaria prevention</li>
</ul>

<p>Of the 400+ households visited, 67 individuals were identified as requiring follow-up care and were referred to the nearest clinic, with Wild4Life providing transport assistance for those who could not afford it.</p>

<h2>Voices from the Community</h2>
<p><em>"I have not been to a clinic in three years. My legs were swelling and I thought it was old age. The nurses told me it is high blood pressure and gave me medicine. Now I know what to do,"</em> said one elderly woman from Ward 4, who asked not to be named.</p>

<p>For the Wild4Life team, moments like these are the reason they do the work. "These are not statistics," says programme coordinator Netsai Dube. "Each one of those 400 families is a life we touched, and hopefully a life we helped protect."</p>

<h2>Support This Work</h2>
<p>Outreaches like this one are made possible entirely through the generosity of donors and partners. Your contribution — however small — helps Wild4Life reach the communities that need it most. <a href="/donate/">Donate today</a> and become part of this story.</p>
""",
    },
    {
        "title": "What Is a Village Health Worker — And Why They Are the Backbone of Community Health",
        "excerpt": (
            "Village Health Workers are often the first — and sometimes only — point of health contact "
            "for families in rural Zimbabwe. Wild4Life's VHW mentorship programme is changing how "
            "these unsung heroes are supported."
        ),
        "content": """
<p>Ask anyone working in rural public health in Zimbabwe and they will tell you the same thing: the Village Health Worker (VHW) is the most important person in the community health system. Yet for decades, these frontline workers have operated with minimal training, little supervision, and almost no recognition.</p>

<p>Wild4Life is working to change that.</p>

<h2>Who Are Village Health Workers?</h2>
<p>VHWs are community members — usually women — selected by their own communities to serve as the first point of contact between households and the formal health system. They are not doctors or nurses. They are neighbours, mothers, grandmothers who have received basic health training and agreed to serve their communities voluntarily.</p>

<p>Their responsibilities are vast:</p>
<ul>
  <li>Monthly household visits to track the health of pregnant women, infants, and elderly residents</li>
  <li>Referrals to clinics for symptoms that need professional attention</li>
  <li>Health education on topics like nutrition, sanitation, family planning, and malaria prevention</li>
  <li>Tracking immunisation schedules for children under five</li>
  <li>First-response support during health emergencies before formal services arrive</li>
</ul>

<h2>The Problem: VHWs Are Often Working Alone</h2>
<p>Despite how critical their role is, most VHWs receive their initial training and are then left largely unsupported. Supervisory visits from clinic staff are infrequent. Equipment like blood pressure cuffs and weighing scales wears out and is rarely replaced. Questions go unanswered. Motivation fades.</p>

<p>This is the gap that Wild4Life's VHW Mentorship Programme is designed to close.</p>

<h2>How Wild4Life's Mentorship Model Works</h2>
<p>Wild4Life pairs experienced clinical mentors — registered nurses and nurse aides — with clusters of VHWs in the districts where it operates. Each mentor is responsible for a group of 8–12 VHWs and conducts:</p>
<ul>
  <li><strong>Monthly structured mentorship visits</strong> to each VHW's household and community</li>
  <li><strong>On-the-job coaching</strong> — reviewing case notes, practising skills, and problem-solving together</li>
  <li><strong>Quarterly group learning sessions</strong> where VHWs across a ward share experiences</li>
  <li><strong>Equipment checks and restocking</strong> of basic health supplies</li>
</ul>

<p>The results speak for themselves. In districts where the programme has been active for more than 12 months, VHW retention has improved by over 35%, and community-level health indicators — including antenatal care uptake and child immunisation rates — have shown measurable improvement.</p>

<h2>Recognising the People Who Show Up Every Day</h2>
<p>"We want every VHW to feel that what they do matters — because it does," says Wild4Life Executive Director. "When a VHW feels supported and valued, she stays. When she stays, her community stays healthy. It really is that simple."</p>

<p>If you would like to support Wild4Life's work with VHWs across rural Zimbabwe, please consider <a href="/donate/">making a donation</a>. Every dollar goes directly to the communities that need it most.</p>
""",
    },
    {
        "title": "Differentiated Service Delivery: Reaching Patients Where They Are",
        "excerpt": (
            "Not every patient can travel to a clinic. Wild4Life's differentiated service delivery "
            "model ensures that people living with chronic conditions continue receiving care — "
            "on their terms, in their communities."
        ),
        "content": """
<p>Healthcare delivery is not one-size-fits-all. A young mother with three children and no transport cannot make a monthly clinic visit. An elderly man managing both HIV and hypertension should not have to choose which condition to prioritise based on which clinic day is available. A teenager newly initiated on antiretroviral therapy needs a level of support that a busy clinic hallway cannot always provide.</p>

<p>Differentiated Service Delivery (DSD) is an approach that recognises these realities and reorganises care around the needs of the patient — not the convenience of the system. Wild4Life has been implementing DSD models in partnership with the Ministry of Health and Child Care since 2019, with remarkable results.</p>

<h2>Our DSD Approaches</h2>

<h3>Community Adherence Groups (CAGs)</h3>
<p>Stable patients on antiretroviral therapy are organised into small groups of 6–12 people. Each month, one member visits the clinic on behalf of the whole group and collects medication for everyone. This reduces the burden on both patients and clinics while keeping people engaged and accountable to each other.</p>

<h3>Fast-Track Refills</h3>
<p>For patients who are stable, virally suppressed, and self-managing well, we work with clinics to provide three- or six-month medication refills with minimal waiting time. What used to take half a day now takes under an hour.</p>

<h3>Community Drug Distribution Points</h3>
<p>In areas where distance to a clinic is a major barrier, Wild4Life supports the establishment of community drug distribution points — often at a trusted community member's home, a church, or a community centre — where stable patients can collect their medications close to home.</p>

<h3>Teen Clubs and Youth-Friendly Services</h3>
<p>Adolescents living with HIV face unique social and psychological challenges. Wild4Life supports teen clubs at facility and community level, providing peer support, counselling, and a safe space to ask questions that they may not feel comfortable asking in a general clinic setting.</p>

<h2>The Impact So Far</h2>
<p>Across our programme areas, patients enrolled in DSD models show:</p>
<ul>
  <li>Higher rates of viral load suppression compared to standard care</li>
  <li>Significantly lower rates of being lost to follow-up</li>
  <li>Greater satisfaction with their care experience</li>
  <li>Improved adherence to medication schedules</li>
</ul>

<p>More importantly, they report feeling treated with dignity — like individuals, not case numbers.</p>

<p>Wild4Life believes that the future of sustainable healthcare in Zimbabwe lies in community-centred models like these. <a href="/donate/">Support our work</a> and help us scale what is working.</p>
""",
    },
    {
        "title": "Clinical Mentorship in Practice: Strengthening the Skills of Frontline Nurses",
        "excerpt": (
            "Wild4Life's clinical mentorship programme does not just deliver training — it "
            "stays alongside healthcare workers month after month, building confidence and "
            "competence where it counts most: at the bedside."
        ),
        "content": """
<p>Training a nurse takes years. But a one-week refresher course, however well-designed, cannot transform clinical practice on its own. Skills learned in a classroom fade. New challenges emerge. Confidence wavers in the face of a complex patient without a supervisor nearby.</p>

<p>Clinical mentorship is different. It is sustained, practical, and human. And it is at the heart of what Wild4Life does.</p>

<h2>What Our Mentors Do</h2>
<p>Wild4Life deploys experienced registered nurses and clinical officers as mentors to health facilities across our programme districts. These are not inspectors or assessors — they are colleagues and coaches. Each mentor is assigned a cluster of facilities and visits regularly, working side-by-side with the health workers stationed there.</p>

<p>During a typical mentorship visit, a Wild4Life mentor will:</p>
<ul>
  <li>Review case files alongside the facility nurse, discussing clinical decision-making</li>
  <li>Observe patient consultations and provide real-time, constructive feedback</li>
  <li>Demonstrate clinical skills — such as PIMA CD4 testing or MUAC measurement — and then watch the nurse practise with guidance</li>
  <li>Review data quality and help nurses understand how to use their own numbers to improve care</li>
  <li>Discuss challenges openly and problem-solve together</li>
  <li>Set goals for the next visit and follow up on progress</li>
</ul>

<h2>Building Confidence, Not Dependency</h2>
<p>The goal of mentorship is not to create facilities that need Wild4Life forever. It is to build the skills, systems, and confidence that allow health workers to thrive independently. Our mentorship model is explicitly designed to gradually reduce the frequency of visits as a facility's capacity grows — a process we call "transitioning to sustainability."</p>

<p>"When I started, I was afraid to manage complicated patients on my own," recalls one nurse at a rural clinic in Lupane. "Now I feel confident. I know what to do, and I know who to call when I don't. That is what mentorship gave me."</p>

<h2>Results That Matter</h2>
<p>Facilities supported by Wild4Life clinical mentorship have recorded improvements across a range of quality-of-care indicators, including:</p>
<ul>
  <li>Improved documentation and patient record completeness</li>
  <li>Faster identification and management of treatment failure</li>
  <li>Increased uptake of viral load testing among eligible patients</li>
  <li>Reduced stock-outs through better supply chain management at facility level</li>
</ul>

<p>Behind each of these numbers is a health worker who is better equipped, a patient who received better care, and a community that is healthier for it.</p>

<p>Would you like to support the mentors who support the nurses who support the communities? <a href="/donate/">Your donation makes this possible.</a></p>
""",
    },
    {
        "title": "Community Dialogues: When Communities Lead Their Own Health",
        "excerpt": (
            "Wild4Life's community dialogue model puts communities in the driver's seat of their "
            "own health outcomes — shifting the conversation from 'what is being done for us' "
            "to 'what are we doing together.'"
        ),
        "content": """
<p>Real, lasting change in community health does not happen from the outside in. It happens when communities themselves understand the problems they face, own the solutions, and hold each other — and their leaders — accountable. This is the philosophy behind Wild4Life's Community Dialogue approach.</p>

<h2>What Is a Community Dialogue?</h2>
<p>A community dialogue is a structured, facilitated conversation held within a community — in a school hall, under a tree, at a chief's homestead — where community members come together to discuss health challenges that affect them directly.</p>

<p>These are not lectures. Wild4Life facilitators do not arrive with all the answers. Instead, they ask questions, create a safe space for honest conversation, and guide the community through a process of:</p>
<ul>
  <li><strong>Understanding:</strong> What health challenges are we facing? What is causing them?</li>
  <li><strong>Prioritising:</strong> Which problems affect the most people? Which can we address ourselves?</li>
  <li><strong>Planning:</strong> What actions can we take as a community? What do we need from outside?</li>
  <li><strong>Acting:</strong> Who is responsible for each action, and by when?</li>
  <li><strong>Reviewing:</strong> Did our actions work? What do we need to do differently?</li>
</ul>

<h2>Topics That Communities Raise</h2>
<p>Wild4Life does not set the agenda. Communities do. Some of the most common issues raised in dialogues across our programme areas include:</p>
<ul>
  <li>Stigma around HIV — and how it stops people from testing or disclosing</li>
  <li>Barriers to antenatal care, including transport, cost, and cultural practices</li>
  <li>The role of traditional healers and how to work with them rather than around them</li>
  <li>Gender-based violence and its link to health outcomes</li>
  <li>Nutrition and food security, particularly for children under five</li>
  <li>Water and sanitation challenges that drive diarrhoeal disease</li>
</ul>

<h2>When Communities Act</h2>
<p>Some of the most powerful outcomes from community dialogues are the ones that Wild4Life had no part in planning. In one ward in Binga, community members decided after a dialogue to establish a community fund to help mothers pay for transport to the clinic for deliveries. In another, male leaders agreed to participate in a "men's corner" at the local health facility to encourage other men to support their partners in accessing maternal care.</p>

<p>These are not Wild4Life's achievements. They are the community's achievements. Wild4Life simply created the conditions for them to happen.</p>

<h2>Join the Conversation</h2>
<p>Community dialogue is low-cost, high-impact work that requires commitment more than resources. But it does require resources — for facilitator training, community mobilisation, and the follow-up that turns conversations into action. <a href="/donate/">Please consider supporting this work.</a></p>
""",
    },
    {
        "title": "Five Years in Lupane: A Story of What Consistent Commitment Looks Like",
        "excerpt": (
            "Five years ago, Wild4Life began working in Lupane District with a small team and "
            "a clear mission. Here is what sustained, community-centred work looks like when "
            "you stay long enough to see the change."
        ),
        "content": """
<p>There is a temptation in the NGO world to measure impact in project cycles — a three-year grant, a two-year intervention, a six-month pilot. Wild4Life has always believed that meaningful change in community health cannot be rushed. You have to stay. You have to build trust. You have to be there when things go wrong, not just when they go well.</p>

<p>This year marks five years of Wild4Life's presence in Lupane District. Here is what that consistency has made possible.</p>

<h2>Year One: Learning and Listening</h2>
<p>When Wild4Life first arrived in Lupane in 2021, the team did not arrive with a programme. They arrived with questions. Who are the Village Health Workers? What do they feel supported in doing, and where do they feel stuck? What are the biggest barriers to care for families in this district? What has been tried before, and why did it or didn't it work?</p>

<p>The first year was almost entirely about listening, relationship-building, and mapping. No programmes. No deliverables. Just presence and respect.</p>

<h2>Year Two and Three: Building the Foundation</h2>
<p>With that foundation in place, Wild4Life began its clinical mentorship programme at six facilities in Lupane, pairing experienced nurses with the facility-based staff who most needed support. Community dialogues began in the wards with the lowest antenatal care and immunisation rates. The VHW mentorship model was introduced, initially with 18 VHWs across three wards.</p>

<p>By the end of year three, the numbers were already telling a story. Antenatal care first-visit attendance in the programme wards had increased by 22%. VHW retention — historically a challenge — was at 94%. Viral load testing uptake had increased by 31% at mentored facilities.</p>

<h2>Years Four and Five: Scaling What Works</h2>
<p>The last two years have been about deepening and expanding. The number of VHWs in the mentorship programme grew to 64. Two additional health facilities joined the clinical mentorship cohort. A teen club was established at the district hospital. And for the first time, community dialogue graduates began facilitating their own dialogues — communities becoming their own engines of change.</p>

<h2>What Five Years Looks Like</h2>
<p>It looks like a nurse in Lupane who tells you, without prompting, that she no longer fears difficult patients because she knows exactly who to call and what to do. It looks like a VHW who has been with the programme since day one and has no intention of leaving. It looks like a community that took a conversation about maternal health and turned it into a locally funded transport fund that is still running two years later.</p>

<p>It looks like slow, ordinary, extraordinary change.</p>

<p>Wild4Life is committed to continuing this work — in Lupane and beyond. If you believe in what sustained community health investment can achieve, <a href="/donate/">we would love your support.</a></p>
""",
    },
]


class Command(BaseCommand):
    help = "Seed 6 sample published blog posts for the Wild4Life website."

    def handle(self, *args, **options) -> None:
        if BlogPost.objects.exists():
            self.stdout.write(
                self.style.WARNING("Blog posts already exist — skipping seed to avoid duplicates.")
            )
            return

        author = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()

        now = timezone.now()
        created = 0

        for i, data in enumerate(POSTS):
            published_at = now - timezone.timedelta(days=i * 9)
            BlogPost.objects.create(
                title=data["title"],
                excerpt=data["excerpt"],
                content=data["content"].strip(),
                author=author,
                status="published",
                published_at=published_at,
            )
            created += 1
            self.stdout.write(f"  Created: {data['title']}")

        self.stdout.write(self.style.SUCCESS(f"\n{created} blog posts created successfully."))
