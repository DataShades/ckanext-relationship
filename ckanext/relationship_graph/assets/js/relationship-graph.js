this.ckan.module("relationship-graph", function ($) {
  "use strict";

  return {
    initialize: function () {
      this.canvas = this.el.find('[data-graph-role="canvas"]');
      this.viewport = this.el.find('[data-graph-role="viewport"]');
      this.status = this.el.find('[data-graph-role="status"]');
      this.meta = this.el.find('[data-graph-role="meta"]');
      this.legend = this.el.find('[data-graph-role="legend"]');
      this.tooltip = this.el.find('[data-graph-role="tooltip"]');
      this.depthControl = this.el.find('[data-graph-role="depth"]');
      this.labelsToggle = this.el.find('[data-graph-role="labels-toggle"]');
      this.fitButton = this.el.find('[data-graph-role="fit"]');
      this.reloadButton = this.el.find('[data-graph-role="reload"]');
      this.downloadButton = this.el.find('[data-graph-role="download"]');
      this.cy = null;
      this.request = null;

      this.config = this._readConfig();

      this._setDownloadEnabled(false);
      this._bindEvents();
      this._loadGraph(this.config.depth);
    },

    teardown: function () {
      if (this.request && typeof this.request.abort === "function") {
        this.request.abort();
      }

      if (this.cy) {
        this.cy.destroy();
        this.cy = null;
      }
    },

    _bindEvents: function () {
      var module = this;

      if (this.depthControl.length) {
        this.depthControl.on("change", function () {
          var depth = parseInt(this.value, 10) || 1;
          module.config.depth = depth;
          module._loadGraph(depth);
        });
      }

      if (this.fitButton.length) {
        this.fitButton.on("click", function () {
          if (module.cy) {
            module.cy.fit(undefined, 32);
          }
        });
      }

      if (this.reloadButton.length) {
        this.reloadButton.on("click", function () {
          module._loadGraph(module.config.depth);
        });
      }

      if (this.downloadButton.length) {
        this.downloadButton.on("click", function () {
          module._downloadGraph();
        });
      }

      if (this.labelsToggle.length) {
        this.labelsToggle.on("change", function () {
          module.config.showLabels = $(this).is(":checked");
          module._applyNodeLabelVisibility();
        });
      }
    },

    _readConfig: function () {
      var el = this.el[0];
      var relationTypes = [];

      try {
        relationTypes = JSON.parse(el.getAttribute("data-relation-types") || "[]");
      } catch (err) {
        relationTypes = [];
      }

      return {
        endpoint: el.getAttribute("data-graph-endpoint"),
        objectId: el.getAttribute("data-object-id"),
        objectEntity: el.getAttribute("data-object-entity") || "package",
        objectType: el.getAttribute("data-object-type") || "dataset",
        depth: parseInt(el.getAttribute("data-depth") || "1", 10),
        maxNodes: parseInt(el.getAttribute("data-max-nodes") || "100", 10),
        showLabels: (el.getAttribute("data-show-labels") || "false") === "true",
        includeUnresolved:
          (el.getAttribute("data-include-unresolved") || "true") === "true",
        layout: el.getAttribute("data-layout") || "cose",
        relationTypes: relationTypes
      };
    },

    _setStatus: function (text, state) {
      this.status
        .removeClass(
          "relationship-graph__status--loading relationship-graph__status--error relationship-graph__status--empty"
        )
        .text(text || "");

      if (state) {
        this.status.addClass("relationship-graph__status--" + state);
      }
    },

    _requestUrl: function (depth) {
      var params = new URLSearchParams({
        object_id: this.config.objectId,
        object_entity: this.config.objectEntity,
        object_type: this.config.objectType,
        depth: String(depth),
        max_nodes: String(this.config.maxNodes),
        include_unresolved: String(this.config.includeUnresolved),
        include_reverse: "true",
        with_titles: "true"
      });

      $.each(this.config.relationTypes, function (_, relationType) {
        params.append("relation_types", relationType);
      });

      return this.config.endpoint + "?" + params.toString();
    },

    _loadGraph: function (depth) {
      var module = this;

      if (this.request && typeof this.request.abort === "function") {
        this.request.abort();
      }

      this._setStatus(this._("Loading relationship graph..."), "loading");
      this.meta.empty();

      this.request = $.ajax({
        url: this._requestUrl(depth),
        method: "GET",
        dataType: "json"
      })
        .done(function (payload) {
          var result = payload.result || payload;
          module._renderGraph(result);
        })
        .fail(function (xhr) {
          var message =
            (xhr.responseJSON &&
              xhr.responseJSON.error &&
              xhr.responseJSON.error.message) ||
            module._("Unable to load graph.");

          module._showError(message);
        });
    },

    _showError: function (message) {
      if (this.cy) {
        this.cy.destroy();
        this.cy = null;
      }

      this.canvas.empty();
      this.legend.empty().hide();
      this._hideTooltip();
      this.meta.empty();
      this._setDownloadEnabled(false);
      this._setStatus(message, "error");
    },

    _setDownloadEnabled: function (enabled) {
      if (this.downloadButton.length) {
        this.downloadButton.prop("disabled", !enabled);
      }
    },

    _cssVar: function (name, fallback) {
      var value = window.getComputedStyle(this.el[0]).getPropertyValue(name).trim();

      return value || fallback;
    },

    _cssNumberVar: function (name, fallback) {
      var value = parseFloat(this._cssVar(name, String(fallback)));

      return Number.isNaN(value) ? fallback : value;
    },

    _readTheme: function () {
      return {
        nodeColor: this._cssVar("--relationship-graph-node-color", "#3f7f8c"),
        nodeBorderColor: this._cssVar(
          "--relationship-graph-node-border-color",
          "#ffffff"
        ),
        nodeBorderWidth: this._cssNumberVar(
          "--relationship-graph-node-border-width",
          2
        ),
        nodeSize: this._cssNumberVar("--relationship-graph-node-size", 34),
        nodeLabelColor: this._cssVar(
          "--relationship-graph-node-label-color",
          "#15323a"
        ),
        nodeLabelFontSize: this._cssNumberVar(
          "--relationship-graph-node-label-font-size",
          11
        ),
        nodeLabelMaxWidth: this._cssNumberVar(
          "--relationship-graph-node-label-max-width",
          120
        ),
        nodeLabelMarginY: this._cssNumberVar(
          "--relationship-graph-node-label-margin-y",
          10
        ),
        unresolvedNodeColor: this._cssVar(
          "--relationship-graph-node-unresolved-color",
          "#c6c7cb"
        ),
        unresolvedNodeLabelColor: this._cssVar(
          "--relationship-graph-node-unresolved-label-color",
          "#4a4d57"
        ),
        nodeHoverBorderColor: this._cssVar(
          "--relationship-graph-node-hover-border-color",
          "#6d8592"
        ),
        centerNodeColor: this._cssVar(
          "--relationship-graph-center-node-color",
          "#e06a3f"
        ),
        centerNodeBorderColor: this._cssVar(
          "--relationship-graph-center-node-border-color",
          "#ffe08a"
        ),
        centerNodeBorderWidth: this._cssNumberVar(
          "--relationship-graph-center-node-border-width",
          6
        ),
        centerNodeSize: this._cssNumberVar(
          "--relationship-graph-center-node-size",
          48
        ),
        centerNodeHaloColor: this._cssVar(
          "--relationship-graph-center-node-halo-color",
          "#ffd166"
        ),
        centerNodeHaloOpacity: this._cssNumberVar(
          "--relationship-graph-center-node-halo-opacity",
          0.3
        ),
        centerNodeHaloPadding: this._cssNumberVar(
          "--relationship-graph-center-node-halo-padding",
          8
        ),
        centerNodeHoverBorderColor: this._cssVar(
          "--relationship-graph-center-node-hover-border-color",
          "#ffe08a"
        ),
        centerNodeHoverHaloOpacity: this._cssNumberVar(
          "--relationship-graph-center-node-hover-halo-opacity",
          0.45
        ),
        centerNodeHoverHaloPadding: this._cssNumberVar(
          "--relationship-graph-center-node-hover-halo-padding",
          10
        ),
        edgeWidth: this._cssNumberVar("--relationship-graph-edge-width", 3),
        edgeHoverWidth: this._cssNumberVar(
          "--relationship-graph-edge-hover-width",
          5
        ),
        edgeOpacity: this._cssNumberVar(
          "--relationship-graph-edge-opacity",
          0.9
        ),
        edgeHoverOpacity: this._cssNumberVar(
          "--relationship-graph-edge-hover-opacity",
          1
        ),
        edgeRelatedToColor: this._cssVar(
          "--relationship-graph-edge-related-to-color",
          "#4a88b5"
        ),
        edgeChildOfColor: this._cssVar(
          "--relationship-graph-edge-child-of-color",
          "#d17a37"
        ),
        edgeParentOfColor: this._cssVar(
          "--relationship-graph-edge-parent-of-color",
          "#4b9b6f"
        ),
        edgeDefaultColor: this._cssVar(
          "--relationship-graph-edge-default-color",
          "#7a8b95"
        )
      };
    },

    _nodeColorForLevel: function (level) {
      var currentLevel = typeof level === "number" ? level : parseInt(level, 10);
      var color = "";

      if (Number.isNaN(currentLevel) || currentLevel <= 0) {
        return this.theme.nodeColor;
      }

      while (currentLevel > 0) {
        color = this._cssVar(
          "--relationship-graph-node-level-" + currentLevel + "-color",
          ""
        );

        if (color) {
          return color;
        }

        currentLevel -= 1;
      }

      return this.theme.nodeColor;
    },

    _relationDefinitions: function () {
      var theme = this.theme || this._readTheme();

      return {
        related_to: {
          color: theme.edgeRelatedToColor,
          label: this._("Related to")
        },
        child_of: {
          color: theme.edgeChildOfColor,
          label: this._("Child of")
        },
        parent_of: {
          color: theme.edgeParentOfColor,
          label: this._("Parent of")
        }
      };
    },

    _relationInfo: function (relationType) {
      var definitions = this._relationDefinitions();

      if (definitions[relationType]) {
        return definitions[relationType];
      }

      return {
        color: (this.theme || this._readTheme()).edgeDefaultColor,
        label: relationType ? relationType.replace(/_/g, " ") : this._("Related")
      };
    },

    _relationOrder: function (relationType) {
      var order = ["related_to", "child_of", "parent_of"];
      var index = $.inArray(relationType, order);

      return index === -1 ? order.length : index;
    },

    _nodeTooltipText: function (node) {
      var title = node.data("title") || node.data("name") || node.id();

      if (node.data("is_center")) {
        return this._("Current dataset: %(title)s", {
          title: title
        });
      }

      return title;
    },

    _renderLegend: function (edges) {
      var module = this;
      var seen = {};
      var relationTypes = [];

      this.legend.empty();

      $.each(edges, function (_, edge) {
        if (seen[edge.relation_type]) {
          return;
        }

        seen[edge.relation_type] = true;
        relationTypes.push(edge.relation_type);
      });

      relationTypes.sort(function (left, right) {
        return module._relationOrder(left) - module._relationOrder(right);
      });

      if (!relationTypes.length) {
        this.legend.hide();
        return;
      }

      this.legend.append(
        $("<div />", {
          class: "relationship-graph__legend-title",
          text: this._("Relation types")
        })
      );

      $.each(relationTypes, function (_, relationType) {
        var relation = module._relationInfo(relationType);
        var item = $("<div />", {
          class: "relationship-graph__legend-item"
        });

        item.append(
          $("<span />", {
            class: "relationship-graph__legend-swatch"
          }).css("background-color", relation.color)
        );
        item.append(
          $("<span />", {
            text: relation.label
          })
        );

        module.legend.append(item);
      });

      this.legend.show();
    },

    _hideTooltip: function () {
      this.tooltip.hide().text("");
    },

    _moveTooltip: function (position) {
      var offset = 14;
      var left = position.x + offset;
      var top = position.y - this.tooltip.outerHeight() - offset;
      var maxLeft = this.viewport.innerWidth() - this.tooltip.outerWidth() - 12;

      if (left > maxLeft) {
        left = maxLeft;
      }

      if (left < 12) {
        left = 12;
      }

      if (top < 12) {
        top = position.y + offset;
      }

      this.tooltip.css({
        left: left + "px",
        top: top + "px"
      });
    },

    _showTooltip: function (text, position) {
      this.tooltip.text(text).show();
      this._moveTooltip(position);
    },

    _slugify: function (value) {
      return (value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    },

    _downloadFilename: function () {
      var centerNode = this.cy ? this.cy.nodes("[?is_center]").first() : null;
      var title =
        centerNode && centerNode.length
          ? centerNode.data("title") || centerNode.data("name")
          : "";
      var baseName =
        this._slugify(title) ||
        this._slugify(this.config.objectId) ||
        "relationship-graph";

      return baseName + ".png";
    },

    _downloadGraph: function () {
      var image;
      var link;

      if (!this.cy || typeof this.cy.png !== "function") {
        return;
      }

      image = this.cy.png({
        full: true,
        scale: 2,
        bg: "#ffffff"
      });
      link = document.createElement("a");
      link.href = image;
      link.download = this._downloadFilename();
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },

    _applyNodeLabelVisibility: function () {
      if (!this.cy) {
        return;
      }

      this.cy.style().selector("node").style({
        label: this.config.showLabels ? "data(title)" : ""
      }).update();
    },

    _renderGraph: function (result) {
      var module = this;
      var nodes = result.nodes || [];
      var edges = result.edges || [];
      var meta = result.meta || {};

      if (typeof cytoscape === "undefined") {
        this._showError(this._("Relationship graph library is not available."));
        return;
      }

      if (this.cy) {
        this.cy.destroy();
      }

      this.theme = this._readTheme();
      this._hideTooltip();

      this.cy = cytoscape({
        container: this.canvas[0],
        elements: []
          .concat(
            $.map(nodes, function (node) {
              return {
                data: $.extend({}, node, {
                  node_color: module._nodeColorForLevel(node.level)
                })
              };
            })
          )
          .concat(
            $.map(edges, function (edge) {
              var relation = module._relationInfo(edge.relation_type);

              return {
                data: $.extend({}, edge, {
                  color: relation.color,
                  relation_label: relation.label
                })
              };
            })
          ),
        style: [
          {
            selector: "node",
            style: {
              label: "",
              "background-color": "data(node_color)",
              color: this.theme.nodeLabelColor,
              "font-size": this.theme.nodeLabelFontSize,
              "font-weight": 600,
              "text-wrap": "wrap",
              "text-max-width": this.theme.nodeLabelMaxWidth,
              "text-valign": "bottom",
              "text-margin-y": this.theme.nodeLabelMarginY,
              width: this.theme.nodeSize,
              height: this.theme.nodeSize,
              "border-width": this.theme.nodeBorderWidth,
              "border-color": this.theme.nodeBorderColor
            }
          },
          {
            selector: "node[?is_center]",
            style: {
              "background-color": this.theme.centerNodeColor,
              "border-width": this.theme.centerNodeBorderWidth,
              "border-color": this.theme.centerNodeBorderColor,
              "underlay-color": this.theme.centerNodeHaloColor,
              "underlay-opacity": this.theme.centerNodeHaloOpacity,
              "underlay-padding": this.theme.centerNodeHaloPadding,
              width: this.theme.centerNodeSize,
              height: this.theme.centerNodeSize
            }
          },
          {
            selector: "node[!resolved]",
            style: {
              "background-color": this.theme.unresolvedNodeColor,
              "border-style": "dashed",
              color: this.theme.unresolvedNodeLabelColor
            }
          },
          {
            selector: "node.is-hovered",
            style: {
              "border-color": this.theme.nodeHoverBorderColor
            }
          },
          {
            selector: "node[?is_center].is-hovered",
            style: {
              "border-color": this.theme.centerNodeHoverBorderColor,
              "underlay-opacity": this.theme.centerNodeHoverHaloOpacity,
              "underlay-padding": this.theme.centerNodeHoverHaloPadding
            }
          },
          {
            selector: "edge",
            style: {
              "curve-style": "bezier",
              "line-color": "data(color)",
              "target-arrow-color": "data(color)",
              "target-arrow-shape": "triangle",
              "arrow-scale": 1,
              width: this.theme.edgeWidth,
              opacity: this.theme.edgeOpacity
            }
          },
          {
            selector: "edge[!directed]",
            style: {
              "target-arrow-shape": "none",
              "line-style": "solid"
            }
          },
          {
            selector: "edge.is-hovered",
            style: {
              width: this.theme.edgeHoverWidth,
              opacity: this.theme.edgeHoverOpacity
            }
          }
        ],
        layout: {
          name: this.config.layout,
          animate: false,
          padding: 32
        }
      });

      this.cy.on("tap", "node", function (event) {
        var url = event.target.data("url");

        if (url) {
          window.location.href = url;
        }
      });

      this.cy.on("mouseover", "node", function (event) {
        event.target.addClass("is-hovered");
        module._showTooltip(
          module._nodeTooltipText(event.target),
          event.renderedPosition
        );
      });

      this.cy.on("mousemove", "node", function (event) {
        module._moveTooltip(event.renderedPosition);
      });

      this.cy.on("mouseout", "node", function (event) {
        event.target.removeClass("is-hovered");
        module._hideTooltip();
      });

      this.cy.on("mouseover", "edge", function (event) {
        event.target.addClass("is-hovered");
        module._showTooltip(
          event.target.data("relation_label"),
          event.renderedPosition
        );
      });

      this.cy.on("mousemove", "edge", function (event) {
        module._moveTooltip(event.renderedPosition);
      });

      this.cy.on("mouseout", "edge", function (event) {
        event.target.removeClass("is-hovered");
        module._hideTooltip();
      });

      this.cy.on("tap", function (event) {
        if (event.target === module.cy) {
          module._hideTooltip();
        }
      });

      this.cy.ready(function () {
        module.cy.fit(undefined, 32);
      });

      this._setDownloadEnabled(true);
      this._applyNodeLabelVisibility();
      this._renderLegend(edges);

      if (!edges.length) {
        this._setStatus(this._("No relationships found."), "empty");
      } else {
        this._setStatus("");
      }

      if (meta.truncated) {
        this.meta.text(
          this._("Graph truncated at %(max)d nodes.", {
            max: meta.max_nodes || this.config.maxNodes
          })
        );
      } else {
        this.meta.empty();
      }
    }
  };
});
