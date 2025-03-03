from textwrap import dedent


def format_software_info(software_info):
    """Format software info into a readable string."""
    vendor = software_info.get("vendor", "N/A")
    product = software_info.get("product", "N/A")
    version = software_info.get("version", "N/A")

    return dedent(
        f"""
        Vendor: {vendor}
        Product: {product}
        Version: {version}
        """
    )


def format_cpe_matches(top_matches):
    """Format CPE matches into a readable string."""
    if not top_matches:
        return "No matches found."

    result = []
    for i, match in enumerate(top_matches, 1):
        cpe_id = match.get("CPE_ID", match.get("ConfigurationsName", "N/A"))
        vendor = match.get("Vendor", "N/A")
        product = match.get("Product", "N/A")
        version = match.get("Version", "N/A")
        target_hardware = match.get("Target_HW", "N/A")

        result.append(
            dedent(
                f"""
                Match #{i}:
                CPE ID: {cpe_id}
                Vendor: {vendor}
                Product: {product}
                Version: {version}
                Target Hardware: {target_hardware}
                """
            )
        )

    return "\n".join(result)
