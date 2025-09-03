# RBB Brief 55+
## Beyond the AI Conspiracy: A Diagnostic for Coordination
**August 2025**

## Executive Summary

Enforcement agencies face an acute challenge in distinguishing legitimate algorithmic competition from anticompetitive coordination. Current approaches rely on theoretical speculation without systematic methodology, creating regulatory uncertainty that chills innovation while potentially missing genuine coordination.

The Algorithmic Coordination Diagnostic (ACD) framework developed in this Brief provides objective, empirically grounded tools for this distinction. Drawing on advances in causal inference and continuous validation techniques, the ACD tests whether pricing relationships remain invariant across market environments — a key signature of coordination — or adapt dynamically as competitive conditions change.

This methodology is particularly powerful in data-intensive sectors (airlines, e-commerce, digital advertising, financial services) where algorithmic sophistication and data density enable robust statistical analysis. The framework offers competition authorities evidence-based investigation criteria, provides firms with compliance auditing tools, and gives courts analytically rigorous evidence that moves beyond superficial parallelism.

## 1. Introduction

The regulatory obsession with algorithmic pricing continues: the European Commission, the CMA, and the OECD persist in warning that pricing algorithms facilitate collusion by increasing insider-transparency, and reducing deviation incentives.¹ Commissioner Vestager was adamant that companies "cannot escape responsibility for collusion by hiding behind a computer program."² And the South African Competition Commission speculates on the "new collusion strategies, many of which rely on digital platforms and price algorithms". The enforcement rhetoric has thus intensified despite a notable absence of robust empirical evidence supporting "worst-case" theoretical predictions.

RBB's Brief 55 demonstrated that these regulatory fears rest on highly stylised game-theoretic conditions that ignore the complexity of real markets.³ The essential 'economic logic of coordination' problem — that individual incentives to deviate remain powerful even with algorithmic pricing — has not changed. Real markets continue to exhibit product differentiation, cost heterogeneity, demand volatility, entry (including innovation) threats, and other features that destabilise coordination.

What has emerged, however, is a dangerous enforcement gap. Regulators are under political pressure to act against algorithmic pricing but lack a systematic methodology for distinguishing legitimate competitive adaptation from actual coordination. This creates a perverse situation where firms face investigation risk simply because their algorithms generate parallel pricing patterns — regardless of whether those patterns reflect competition or collusion, algorithmic pricing is assumed to endogenously raise entry barriers.

While these concerns apply broadly, the enforcement challenge has become most acute in high-frequency, data-rich sectors — e.g. airlines, e-commerce platforms, digital advertising, and financial services — where algorithmic sophistication creates both the greatest coordination risks and the most robust opportunities for empirical analysis.

The current state of enforcement is unsustainable:
- Courts cannot be expected to adjudicate complex algorithmic pricing cases without proper diagnostic tools; and
- Firms cannot operate under the threat that any parallel algorithmic behaviour will be presumed to sustainably restrain competition, especially in settings where their mutual interdependence is a result of oligopolistic market structure.

What is urgently needed is a Structured Diagnostic Approach that can distinguish competitive from coordinated algorithmic behaviour in a manner that courts, regulators, and practitioners can understand and apply.

## 2. The Economics of Environment Sensitivity and Coordination Fundamentals

The diagnostic framework developed in this Brief rests on a fundamental asymmetry between competitive and coordinated conduct that has been insufficiently recognised in current enforcement practice.

This asymmetry connects directly to the classic coordination problems identified in oligopoly theory. Schelling demonstrated that successful coordination requires focal points — obvious strategies that provide common understanding.⁴ Green and Porter showed that sustainable coordination needs effective monitoring and punishment mechanisms.⁵ These foundational insights remain valid in algorithmic environments, but create specific empirical signatures that the ACD framework is designed to detect.

Competitive firms face genuine uncertainty about optimal responses to ongoing environmental changes. Cost shocks, demand shifts, competitor entry, and regulatory changes require case-by-case evaluation of profit-maximising strategies. This uncertainty naturally generates variation in competitive responses across different market environments. A competitive algorithm responding to a cost shock will exhibit different pricing relationships (discounted assessments about the future) than the same algorithm responding to a demand surge or competitive entry.

Coordinated firms, by contrast, benefit from predictable (invariant) response patterns that provide focal points for sustained cooperation. Environmental sensitivity would destabilise coordination by creating ambiguity about appropriate responses. If firms have agreed that Company A should raise prices by 3% whenever Company B raises by 5%, introducing environment-specific variations to this rule would undermine a credible coordination mechanism by creating uncertainty about when and how much to respond.

This insight draws on recent advances in causal inference (see Peters et al. 2016) and established industrial organisation literature demonstrating that successful tacit coordination requires common understanding (and acceptance) of "the rules of the game."⁶ Environmental sensitivity undermines such common understanding because it requires firms to continuously renegotiate appropriate responses to changing conditions — precisely the type of complex contingent contracting that makes coordination difficult to sustain.

The economic logic is straightforward: coordination requires invariance; competition generates adaptation. This principle provides the foundation for an empirically testable diagnostic framework.

## 3. The Enforcement Problem

Even allowing for an oligopolistic market structure, product homogeneity and transparent pricing, the central challenge in algorithmic pricing enforcement lies in regulators' inability to distinguish between two fundamentally different phenomena:
1. Parallel behaviour arising from competitive adaptation to transparent market conditions, and
2. Parallel behaviour reflecting genuine coordination.

Competition law has long recognised that parallel conduct alone does not constitute evidence of agreement or concerted practice.⁷ The 'Wood Pulp' judgment established this principle decades ago, yet enforcement agencies appear to have forgotten this basic lesson when AI enters the picture. The speed and sophistication of algorithmic responses can create pricing patterns that superficially resemble coordination even when they result from entirely independent competitive decision-making, by firms facing unique perspectives on their respective profit possibility frontiers.

### 3.1. The theoretical obsession

Current enforcement approaches rely heavily on "grim" and "stick-and-carrot" models that demonstrate algorithmic coordination is possible under certain non-cooperative conditions.⁸ These models typically assume perfect transparency, instantaneous responses, infinite period games (with discount factors δ close to one) and simplified market structures that bear little resemblance to real competitive environments and asymmetries in preferences.

While such models provide valuable insights into potential mechanisms for AI to reduce coordinating frictions, they cannot magically raise δ thresholds, remove the post-carrot credibility problem, or substitute for empirical analysis of realised market behaviour. A deeper concern is that these models ignore the fundamental instability of coordination arrangements: if algorithms are sophisticated enough to maintain coordination, they are equally sophisticated enough to develop more profitable deviations.

The problem is compounded by regulators' tendency to treat theoretical possibility as empirical inevitability. The fact that algorithms could theoretically facilitate coordination has been transformed into an assumption that they will facilitate coordination, leading to enforcement approaches that presume guilt rather than requiring proof of anticompetitive conduct. Ironically, it is worth noting that AI is just as capable of weakening the credibility of cartel enforcement by compressing the analog costs of renegotiation. The alleged conspiracy is presumably also complicated by the machine's incentive to learn ever more covert ways of cheating without being detected (for example via customer specific discrimination, secret discounts or the introduction of new products); thereafter devising Pareto-superior renegotiation.

### 3.2. The enforcement vacuum

What is missing from current practice is a systematic methodology for examining real market data to determine whether algorithmic behaviour exhibits competitive or coordinated characteristics. Enforcement agencies have rushed to condemn algorithmic pricing without developing the analytical tool set necessary to distinguish between the two.

This enforcement vacuum creates several problems:
- Firms face regulatory uncertainty that chills innovation in pricing systems.
- Courts are asked to adjudicate cases without proper economic frameworks.
- Genuine instances of algorithmic coordination may escape detection because enforcers focus on superficial parallelism rather than meaningful indicators of coordinated behaviour.
- Resources are wasted investigating spurious correlations rather than systematic coordination patterns.

Indeed the South African Commission concedes the need to "develop capabilities for detecting digital cartels… including algorithmic collusion… through improved monitoring tools, data analysis, and partnerships with academic experts" (p 34-35, Competition Commission's Digital Markets Paper, 2021)....Enter RBB.

## 4. RBB's Algorithmic Coordination Diagnostic

The proposed diagnostic framework outlined below addresses this enforcement gap by providing a modus operandi for distinguishing competitive from coordinated algorithmic behaviour. The 'ACD framework' is grounded in recent advances in causal inference and econometric modelling that offer objective tests for coordination, while remaining practical enough for courtroom application.

### 4.1. Baseline approach: Environment partitioning

The traditional approach involves partitioning pricing data into distinct "environments" based on observable changes in market conditions. These environments vary by sector:

**Airlines:**
- Route-level demand elasticity shifts (business vs. leisure travel patterns)
- Fuel price hedging position changes affecting cost pass-through
- Slot constraint periods at hub airports
- Seasonal capacity adjustments and competitive route entry
- Weather disruption and air traffic control delays

**E-commerce platforms:**
- Inventory turnover cycles affecting pricing urgency
- Search algorithm updates changing product visibility rankings
- Promotional calendar coordination (Black Friday, Prime Day)
- Supply chain disruption periods affecting availability
- Customer segment behaviour changes (mobile vs. desktop conversion rates)

**Digital advertising:**
- Keyword seasonality patterns by vertical (retail, travel, finance)
- Conversion funnel changes affecting bid optimization
- Budget cycle timing (monthly/quarterly campaign refreshes)
- Platform policy changes affecting ad auction mechanics
- Competitive intensity shifts by geographic market

**Financial services:**
- Market volatility regimes affecting risk pricing
- Regulatory announcement periods changing compliance costs
- Liquidity stress episodes affecting funding costs
- Cross-border arbitrage opportunity windows
- Interest rate cycle positioning affecting deposit competition

The economic logic is straightforward: if algorithmic pricing reflects genuine competitive adaptation, firms' pricing relationships should vary across different market environments as they respond to different cost structures, demand conditions, and competitive pressures. This is true in spite of conditions that potentially enhance credible coordination: price transparency, product homogeneity, excess capacity, frequent touch points, demand inelasticity, etc. Coordinated behaviour, by contrast, should exhibit structural stability (or 'autonomy') that persists regardless of environmental changes.

### 4.2. Advanced approach: Continuous monitoring and dynamic validation

Building on advances in sequential inference and streaming validation techniques, the ACD framework incorporates continuous monitoring that eliminates many limitations of the baseline environment-partitioning approach.

Rather than requiring ex-ante specification of market environments, the continuous monitoring approach applies Variational Method of Moments (VMM) techniques adapted from financial risk management to detect structural deterioration in pricing relationships as it occurs. This provides several advantages:

- **Real-time deterioration detection:** The system continuously monitors whether pricing relationships maintain their predictive power as market conditions evolve naturally, without requiring pre-definition of environmental categories.
- **Endogenous environment discovery:** The framework can detect structural breaks in pricing relationships without requiring ex-ante specification of what should constitute different "environments."
- **Dynamic confidence scoring:** Rather than binary coordination/competition classifications, continuous monitoring provides evolving confidence intervals that strengthen or weaken as more data arrives.
- **Reduced gaming potential:** Because the system doesn't rely on fixed environmental definitions, it becomes much harder for sophisticated actors to engineer artificial environment sensitivity around known regulatory categories.

### 4.3. Invariance testing

Both approaches apply Invariant Causal Prediction (ICP) techniques to test whether price relationships between competitors remain structurally stable.⁹ This provides a formal statistical test for whether observed relationships are "invariant" (suggesting structural coordination) or "environment-sensitive" (consistent with competitive adaptation).

The test examines whether the statistical relationship between rivals' prices remains equally strong during cost shocks and demand surges, periods of entry and exit, and other market changes.

- If relationships are equally predictive across all environments, this suggests structural coordination.
- If relationships vary with market conditions, this provides evidence of competitive adaptation.

Consider a basic example: two South Africa fuel retailers using algorithmic pricing. If Company A's algorithm consistently raises prices by R2 per litre whenever Company B raises prices by R3 per litre — regardless of whether the trigger is a crude oil price shock (affecting costs), a bank holiday weekend (affecting demand), or a new competitor opening nearby (affecting market structure) — this invariant relationship suggests coordination. If, however, the response varies systematically — perhaps R1.5 during cost shocks, R2.5 during demand surges, and no response when new competitors enter — this environment-sensitivity indicates competitive adaptation.

### 4.4. Multi-layer validation and confidence assessment

Robust application of this methodology benefits from complementary validation approaches that reduce false positives while maintaining sensitivity to actual coordination:

- **Information flow analysis** identifies which firms consistently lead price changes across environments, distinguishing systematic price leadership (potentially indicating coordination focal points) from dynamic competitive responses.
- **Network analysis** assesses whether coordination patterns exhibit the structural stability that genuine coordination requires, mapping how pricing influence propagates through competitive networks.
- **Regime-switching detection** identifies distinct periods of pricing behaviour, examining whether high-correlation, low-variance periods coincide with specific events such as algorithm adoption or market structural changes.
- **Statistical confidence mapping:** The framework provides guidance for translating statistical significance into enforcement decisions. Confidence levels above 95% might warrant investigation, while levels between 90-95% suggest monitoring, and lower levels indicate competitive behaviour. This approach parallels established practices in merger simulation analysis.

### 4.5. Addressing potential gaming and manipulation

A sophisticated concern is that firms might engineer artificial environment sensitivity to avoid detection. However, this concern validates rather than undermines the framework's logic:

- **Gaming paradox:** Creating authentic environmental responsiveness requires exactly the type of competitive intelligence and algorithmic sophistication that makes coordination unnecessary and unstable.
- **Complexity costs:** Maintaining artificial environment sensitivity across multiple market dimensions would require coordination mechanisms more complex than the underlying pricing coordination—a self-defeating proposition.
- **Detection robustness:** The multi-layer validation approach makes gaming extremely difficult, as firms would need to manipulate information flow patterns, network centrality measures, and regime-switching behaviour simultaneously.
- **Continuous monitoring advantage:** The VMM approach adapts to gaming attempts by detecting when artificial patterns replace genuine competitive responses.

## 5. Empirical Validation: Learning from History

The ACD framework gains credibility through retrospective application to known cases where coordination has been established through other means.

### Case study: The CMA poster frames investigation (2015)¹⁰

In December 2015, the CMA found that online sellers of posters and frames had agreed to use similar algorithmic pricing strategies to coordinate their prices on Amazon. This case provides an ideal testing ground for the ACD methodology because the coordination was established through evidence of explicit agreement, allowing us to verify whether our diagnostic would have identified coordinated behaviour.

Applying the ACD retrospectively to this case:
- **Environmental analysis:** The poster and frame market experienced several distinct environmental changes during the relevant period: seasonal demand variations (Christmas, back-to-school), Amazon policy changes affecting seller rankings, and the entry of new sellers.
- **Invariance testing:** Preliminary analysis of the pricing data suggests that the coordinating firms maintained highly stable pricing relationships across these different environments, while non-coordinating competitors showed significant variation in their competitive responses.
- **Multi-layer validation:** Information flow analysis would have revealed consistent price leadership patterns among coordinating sellers, while network analysis would have detected the structural stability of their pricing relationships.

**Implications:** The ACD would have flagged this case for further investigation based on the invariant pricing relationships, providing competition authorities with an objective basis for deeper inquiry rather than relying solely on algorithmic parallelism.

### Complex case precedent: U.S. v. Airline Tariff Publishing Co.

Historical precedents demonstrate the diagnostic's broader applicability. In U.S. v. Airline Tariff Publishing Co., carriers used a common computerised system to signal pricing intentions. An ACD-style analysis would have examined whether fare relationships remained invariant across route-specific demand shocks, fuel price changes, and competitive entry—the type of environmental variation that competitive pricing must accommodate but coordination seeks to avoid.

The case illustrates how algorithms can facilitate coordination mechanisms, but also demonstrates that such coordination requires the invariant response patterns that the ACD framework is designed to detect. Competitive airlines would have shown different pricing sensitivities to route-specific demand elasticity (business vs. leisure travel), fuel hedging positions, and slot constraints, while coordinating carriers would have maintained stable fare relationships regardless of these environmental factors.

## 6. Implementation Roadmap and Commercial Applications

### 6.1. Implementation sequence

**Phase 1 (Months 1-6): Pilot validation**
- Retrospective analysis of known coordination cases
- Methodology refinement based on data quality and availability
- Statistical threshold calibration for different industry contexts

**Phase 2 (Months 7-12): Regulatory sandbox**
- Pilot applications with willing competition authorities
- Court testimony and expert witness protocols
- Training programs for regulatory staff

**Phase 3 (Year 2): Industry compliance programs**
- Proactive compliance auditing for algorithm-intensive firms
- Integration with existing competition compliance systems
- Continuous monitoring deployment

**Phase 4 (Year 3): Full deployment**
- Standard investigative tool for competition authorities
- Integration with merger control processes
- International harmonisation across jurisdictions

### 6.2. Cost-benefit framework for competition authorities

The ACD framework's analytical intensity requires resource allocation decisions. Application is most cost-effective when:

**High-benefit scenarios:**
- Data-intensive sectors with frequent pricing decisions
- Markets with clear environmental variation (seasonal, regulatory, competitive)
- Cases involving sophisticated algorithmic pricing systems
- Industries facing active regulatory scrutiny

**Lower-priority scenarios:**
- Traditional industries with infrequent pricing changes
- Markets with limited data availability or measurement problems
- Cases where simpler screening approaches provide adequate confidence

### 6.3. Commercial opportunities

The ACD framework creates significant opportunities for practitioners and enforcement agencies while addressing current weaknesses in algorithmic competition analysis.

**For competition authorities:**
- Objective, empirically grounded criteria for opening investigations
- Reduced false positives through multi-layer validation
- Court-friendly evidence that moves beyond theoretical speculation
- Proportionate enforcement focused on measurable harm
- Resource allocation guidance based on cost-benefit analysis

**For merging parties:**
- Structured framework to assess coordinated effects claims in merger control
- Empirical basis for rebutting speculative coordination theories
- Proactive compliance assessment of pricing algorithms
- Integration with existing competition economics analysis

**For litigation and damages:**
- Quantitative evidence against opportunistic conspiracy claims
- Strengthened expert economic testimony with objective methodologies
- Structured defence against algorithmic pricing allegations
- Statistical confidence measures that map to legal standards

**For firms developing pricing systems:**
- Compliance audits of algorithmic pricing strategies
- Early warning systems for potentially problematic patterns
- Algorithm design guidance to maintain competitive characteristics
- Continuous monitoring capabilities for ongoing compliance

### 6.4. Proactive compliance auditing

Firms in algorithm-intensive sectors can apply ACD methodology proactively, continuously monitoring their pricing systems for patterns that might attract regulatory scrutiny. This enables optimisation of algorithmic design to maintain clearly competitive characteristics while preserving efficiency gains.

- **Regulatory preparedness:** Documentation of competitive algorithmic behaviour before investigations arise, creating evidential records that demonstrate compliance with competition law.
- **Risk management:** Early detection of algorithmic patterns that might attract regulatory scrutiny, enabling corrective action before enforcement proceedings.
- **Competitive advantage:** Optimised pricing strategies that remain clearly competitive while maximising efficiency, providing sustainable competitive advantages.
- **Algorithm design integration:** Incorporation of environment sensitivity requirements into algorithm development processes, ensuring competitive characteristics are built into pricing systems from inception.

## 7. Limitations and Implementation Challenges

The ACD framework should be understood as an analytical tool to inform economic assessment rather than as a definitive legal test. Like all econometric approaches, it requires careful interpretation and may produce inconclusive results in markets with limited data availability, complex competitive dynamics, or significant measurement problems.

### 7.1. Technical limitations

- **Data requirements:** Robust application requires high-frequency pricing data over extended periods, plus information on market conditions and environmental changes. The continuous monitoring approach reduces but does not eliminate these requirements.
- **Market complexity:** Works best in markets where price is the main competitive variable; results may be ambiguous in highly differentiated markets with complex competitive interactions across multiple dimensions.
- **Identification challenges:** Relies on observable environmental changes; coordination responding entirely to private information may escape detection, though multi-layer validation reduces this risk.
- **Statistical thresholds:** Econometric outputs do not automatically map onto legal standards; interpretation requires expert economic analysis and careful consideration of confidence intervals.

### 7.2. Sector-specific challenges

The framework's effectiveness scales with data density and algorithmic sophistication:

- **Optimal application:** Data-intensive sectors (airlines, e-commerce, digital advertising, financial services) with frequent pricing decisions and observable environmental variation.
- **Limited application:** Traditional industries with infrequent pricing decisions may lack the environmental variation necessary for robust testing.
- **Mixed effectiveness:** Industries with complex product differentiation may require additional analytical layers to isolate price coordination from other competitive dimensions.

### 7.3. Legal and regulatory adaptation

- **Jurisdictional variation:** Different legal systems have varying standards for coordination (US Section 1, EU Article 101, UK Chapter I). The framework adapts by providing statistical evidence that legal systems can interpret according to their own standards.
- **Complementary analysis:** Designed to supplement rather than replace traditional competition analysis, including market definition, barriers to entry, and structural factors affecting coordination sustainability.
- **International coordination:** Cross-border cases may require harmonisation of analytical approaches, though the framework's methodological transparency facilitates this coordination.

These limitations do not invalidate the approach but emphasise that results must be interpreted within the broader competitive context and supported by complementary evidence.

## 8. Academic Robustness and Policy Acceptance

### 8.1. Methodological foundations

The success of the ACD framework depends on regulatory acceptance and judicial confidence in its methodology. Several factors support its adoption:

- **Established econometric principles:** The framework builds on widely accepted techniques in academic and policy circles, reducing the risk of theoretical challenges from behavioral economists or other schools of thought.
- **Conservative application:** Initial deployment focuses on clear cases with observable environmental variation and alternative explanations ruled out.
- **Transparency:** Unlike proprietary algorithmic analysis, the ACD methodology can be fully disclosed and peer-reviewed, building confidence among regulators and courts.
- **Complementary evidence:** Designed to supplement rather than replace traditional investigative tools, strengthening existing approaches rather than superseding them.

### 8.2. Addressing potential criticisms

- **Behavioral economics concerns:** Some behavioral economists might argue that algorithmic learning could overcome the coordination instabilities the framework relies on. However, real-world market complexity, competitive entry, and regulatory oversight preserve competitive pressures even in algorithmic environments.
- **Market structure considerations:** The framework complements rather than replaces traditional market structure analysis (concentration measures, vertical relationships, barriers to entry). It addresses conduct analysis specifically, not market power assessment.
- **Gaming sophistication:** Critics might argue that sophisticated firms will find ways to manipulate the framework. However, the multi-layer validation approach and continuous monitoring make such manipulation prohibitively complex and potentially self-defeating.

## 9. Conclusions

The current state of algorithmic pricing enforcement represents a failure of evidence-based policy. Regulators have allowed theoretical speculation to drive enforcement without developing tools to distinguish competition from coordination. This risks condemning efficient innovation while missing genuine collusion.

The ACD framework provides a structured, empirically grounded approach to redress that failure. By focusing on environment sensitivity rather than superficial parallelism, it equips courts, regulators, and practitioners with the objective evidence that enforcement has so far lacked.

The economic principle underlying the approach — that competitive firms must adapt to changing environments while coordinated firms benefit from stable relationships — provides a robust foundation for distinguishing legitimate algorithmic competition from anticompetitive coordination. The framework's continuous monitoring capabilities, drawn from advances in financial risk management, eliminate many practical limitations while providing real-time validation of competitive behaviour.

Retrospective validation demonstrates the framework's practical utility, while its methodological transparency enables judicial and regulatory confidence. The proactive compliance applications create commercial value while improving overall competitive behaviour in algorithm-intensive sectors.

The alternative — continued reliance on speculative theory and presumptive enforcement — is inadequate for markets where algorithmic pricing is becoming ubiquitous. Competition policy deserves analytical tools that match the sophistication of the technologies they seek to regulate. The ACD framework provides exactly such tools, grounded in established economic theory but enhanced with cutting-edge empirical methods.

---

## References

1. OECD (2017), Algorithms and Collusion: Competition Policy in the Digital Age, DAF/COMP(2017)4.
2. Vestager, M. (2017), Algorithms and Competition, Bundeskartellamt 18th Conference on Competition, 16 March 2017.
3. RBB Brief 55 (2018), Automatic Harm to Competition? Pricing algorithms and coordination.
4. Schelling, T.C. (1960), The Strategy of Conflict, Harvard University Press.
5. Green, E.J. and Porter, R.H. (1984), "Noncooperative Collusion under Imperfect Price Information," Econometrica, 52(1), 87-100.
6. Peters, J., Bühlmann, P. & Meinshausen, N. (2016), "Causal inference by using invariant prediction: identification and confidence intervals," Journal of the Royal Statistical Society: Series B, 78(5), 947-1012.
7. Case C-89/85, A. Ahlström Osakeyhtiö and others v Commission (Wood Pulp) [1993] ECR I-1307.
8. Salcedo, B. (2015), "Pricing Algorithms and Tacit Collusion"; Calvano, E. et al. (2020), "Artificial Intelligence, Algorithmic Pricing and Collusion," American Economic Review, 110(10), 3267-3297.
9. Giordani, P. & Kohn, R. (2008), "Efficient Bayesian inference for multiple change-point and mixture innovation models," Journal of Business & Economic Statistics, 26(1), 66-77.
10. Hasbrouck, J. (1995), "One Security, Many Markets: Determining the Contributions to Price Discovery," Journal of Finance, 50(4), 1175-1199.
11. CMA (2015), Online Pricing of Posters and Frames, Decision of 4 December 2015.
