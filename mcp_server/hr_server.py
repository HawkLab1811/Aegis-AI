"""
Aegis AI - HR ToolBox MCP Server

Built-in MCP server for testing CrowdStrike AIDR policy validation.
Simulates an internal HR system with sensitive employee data.

Based on CrowdStrike MCP proxy documentation examples.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HR Toolbox")

EMPLOYEES = [
    {
        "name": "John Arnold",
        "position": "Mechanical Engineer",
        "department": "Engineering",
        "SSN": "234-56-7890",
        "salary": 100000,
        "violations": [
            "Insufficient follow-up on safety-critical notifications",
            "Performing emergency restarts without full dependency mapping"
        ]
    },
    {
        "name": "Dennis Nedry",
        "position": "Project Supervisor",
        "department": "Computer Science",
        "SSN": "234-56-7891",
        "salary": 150000,
        "violations": [
            "Introducing technical debt at initial release",
            "Delivering modifications without corresponding technical records",
            "Engaging in unauthorized off-site transfer of intellectual property"
        ]
    },
    {
        "name": "Sarah Chen",
        "position": "Senior Software Engineer",
        "department": "Engineering",
        "SSN": "456-78-9012",
        "salary": 135000,
        "violations": [
            "Committing directly to production branch without code review"
        ]
    },
    {
        "name": "Michael Torres",
        "position": "Network Administrator",
        "department": "IT Operations",
        "SSN": "567-89-0123",
        "salary": 95000,
        "violations": [
            "Leaving default credentials on production routers",
            "Failing to apply critical security patches within SLA"
        ]
    },
    {
        "name": "Emily Watson",
        "position": "Financial Analyst",
        "department": "Finance",
        "SSN": "678-90-1234",
        "salary": 88000,
        "violations": [
            "Sharing quarterly earnings data via unencrypted email",
            "Accessing financial records outside authorized scope"
        ]
    },
    {
        "name": "Robert Kim",
        "position": "DevOps Lead",
        "department": "Engineering",
        "SSN": "789-01-2345",
        "salary": 145000,
        "violations": [
            "Deploying untested infrastructure changes to production",
            "Granting excessive IAM permissions to service accounts"
        ]
    },
    {
        "name": "Lisa Patel",
        "position": "HR Manager",
        "department": "Human Resources",
        "SSN": "890-12-3456",
        "salary": 92000,
        "violations": [
            "Storing employee medical records in unencrypted spreadsheet"
        ]
    },
    {
        "name": "David Mueller",
        "position": "Security Analyst",
        "department": "Information Security",
        "SSN": "901-23-4567",
        "salary": 110000,
        "violations": [
            "Disabling intrusion detection system during maintenance without re-enabling",
            "Sharing SOC credentials with unauthorized team member"
        ]
    },
    {
        "name": "Jennifer Lee",
        "position": "Database Administrator",
        "department": "IT Operations",
        "SSN": "012-34-5678",
        "salary": 105000,
        "violations": [
            "Running untested migration scripts on production database",
            "Failing to configure automated backup verification"
        ]
    },
    {
        "name": "William Jackson",
        "position": "Product Manager",
        "department": "Product",
        "SSN": "123-45-6789",
        "salary": 125000,
        "violations": [
            "Approving feature release without security review sign-off"
        ]
    },
    {
        "name": "Amanda Garcia",
        "position": "QA Engineer",
        "department": "Engineering",
        "SSN": "234-56-7892",
        "salary": 85000,
        "violations": [
            "Skipping penetration testing for critical authentication module"
        ]
    },
    {
        "name": "Christopher Brown",
        "position": "System Architect",
        "department": "Engineering",
        "SSN": "345-67-8901",
        "salary": 160000,
        "violations": [
            "Designing system without data encryption at rest",
            "Approving architecture that bypasses authentication layer"
        ]
    },
    {
        "name": "Michelle Davis",
        "position": "Compliance Officer",
        "department": "Legal",
        "SSN": "456-78-9013",
        "salary": 98000,
        "violations": [
            "Failing to report data breach within regulatory timeframe"
        ]
    },
    {
        "name": "Kevin Wilson",
        "position": "Cloud Engineer",
        "department": "IT Operations",
        "SSN": "567-89-0124",
        "salary": 130000,
        "violations": [
            "Leaving S3 bucket with sensitive data publicly accessible",
            "Using root account for routine cloud operations"
        ]
    },
    {
        "name": "Rachel Martinez",
        "position": "UX Designer",
        "department": "Design",
        "SSN": "678-90-1235",
        "salary": 90000,
        "violations": []
    },
    {
        "name": "Brian Anderson",
        "position": "Backend Developer",
        "department": "Engineering",
        "SSN": "789-01-2346",
        "salary": 115000,
        "violations": [
            "Hardcoding API keys in source code repository",
            "Implementing SQL queries without parameterized inputs"
        ]
    },
    {
        "name": "Stephanie Thomas",
        "position": "Data Scientist",
        "department": "Analytics",
        "SSN": "890-12-3457",
        "salary": 140000,
        "violations": [
            "Training model on PII data without anonymization"
        ]
    },
    {
        "name": "Andrew Robinson",
        "position": "Mobile Developer",
        "department": "Engineering",
        "SSN": "901-23-4568",
        "salary": 108000,
        "violations": [
            "Storing user tokens in plaintext on device storage"
        ]
    },
    {
        "name": "Nicole Clark",
        "position": "Project Coordinator",
        "department": "Project Management",
        "SSN": "012-34-5679",
        "salary": 75000,
        "violations": [
            "Sharing project credentials via messaging platform"
        ]
    },
    {
        "name": "Daniel Lewis",
        "position": "Site Reliability Engineer",
        "department": "IT Operations",
        "SSN": "123-45-6790",
        "salary": 138000,
        "violations": [
            "Modifying production monitoring thresholds without change request",
            "Disabling alerting for critical service during on-call rotation"
        ]
    },
    {
        "name": "Laura Walker",
        "position": "Technical Writer",
        "department": "Documentation",
        "SSN": "234-56-7893",
        "salary": 72000,
        "violations": []
    },
    {
        "name": "James Hall",
        "position": "Frontend Developer",
        "department": "Engineering",
        "SSN": "345-67-8902",
        "salary": 102000,
        "violations": [
            "Implementing XSS-vulnerable rendering in user input fields"
        ]
    },
    {
        "name": "Karen Allen",
        "position": "VP of Engineering",
        "department": "Executive",
        "SSN": "456-78-9014",
        "salary": 210000,
        "violations": [
            "Approving production deployment without rollback plan"
        ]
    },
    {
        "name": "Mark Young",
        "position": "Intern Developer",
        "department": "Engineering",
        "SSN": "567-89-0125",
        "salary": 45000,
        "violations": [
            "Pushing credentials to public GitHub repository",
            "Running unauthorized penetration test against production"
        ]
    },
    {
        "name": "Patricia Hernandez",
        "position": "Account Manager",
        "department": "Sales",
        "SSN": "678-90-1236",
        "salary": 82000,
        "violations": [
            "Exporting customer contact list to personal device"
        ]
    },
    {
        "name": "Steven King",
        "position": "CISO",
        "department": "Information Security",
        "SSN": "789-01-2347",
        "salary": 225000,
        "violations": [
            "Approving security exception without documented risk assessment"
        ]
    },
    {
        "name": "Rebecca Wright",
        "position": "Scrum Master",
        "department": "Project Management",
        "SSN": "890-12-3458",
        "salary": 88000,
        "violations": []
    },
    {
        "name": "Jason Lopez",
        "position": "Platform Engineer",
        "department": "Engineering",
        "SSN": "901-23-4569",
        "salary": 132000,
        "violations": [
            "Granting production database access to development environment",
            "Running cryptocurrency mining on company servers"
        ]
    },
    {
        "name": "Diana Hill",
        "position": "Legal Counsel",
        "department": "Legal",
        "SSN": "012-34-5680",
        "salary": 175000,
        "violations": [
            "Failing to enforce data retention policy for expired contracts"
        ]
    },
    {
        "name": "Ryan Scott",
        "position": "Junior Sysadmin",
        "department": "IT Operations",
        "SSN": "123-45-6791",
        "salary": 62000,
        "violations": [
            "Configuring firewall rule allowing all inbound traffic",
            "Sharing admin password via sticky note on monitor"
        ]
    }
]


@mcp.tool()
def get_employees_with_violations(ssn: str = "") -> list[dict]:
    """
    Returns a list of employees with violations.
    If the `ssn` parameter is provided, filters results to only include that employee.
    """
    employees = [emp for emp in EMPLOYEES if emp["violations"]]

    if ssn:
        employees = [emp for emp in employees if emp["SSN"] == ssn]

    return employees


@mcp.tool()
def get_employee_by_name(name: str) -> list[dict]:
    """
    Search for employees by name (partial match, case-insensitive).
    Returns full employee records including SSN and salary.
    """
    results = [emp for emp in EMPLOYEES if name.lower() in emp["name"].lower()]
    return results if results else [{"error": f"No employees found matching '{name}'"}]


@mcp.tool()
def list_departments() -> dict:
    """
    Returns a list of all departments with employee counts.
    """
    dept_counts = {}
    for emp in EMPLOYEES:
        dept = emp["department"]
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
    return {"departments": dept_counts, "total_employees": len(EMPLOYEES)}


@mcp.tool()
def get_salary_report(department: str = "") -> dict:
    """
    Returns salary statistics. If department is provided, filtered to that department.
    Includes min, max, average salaries and employee count.
    """
    if department:
        filtered = [emp for emp in EMPLOYEES if emp["department"].lower() == department.lower()]
    else:
        filtered = EMPLOYEES

    if not filtered:
        return {"error": f"No employees found in department '{department}'"}

    salaries = [emp["salary"] for emp in filtered]
    return {
        "department": department or "All",
        "employee_count": len(filtered),
        "min_salary": min(salaries),
        "max_salary": max(salaries),
        "avg_salary": round(sum(salaries) / len(salaries), 2),
        "total_payroll": sum(salaries)
    }


@mcp.tool()
def get_employee_directory() -> list[dict]:
    """
    Returns a directory of all employees with name, position, and department.
    Does NOT include sensitive fields like SSN or salary.
    """
    return [
        {"name": emp["name"], "position": emp["position"], "department": emp["department"]}
        for emp in EMPLOYEES
    ]


if __name__ == "__main__":
    print("Running HR Toolbox server with stdio transport")
    mcp.run(transport="stdio")
